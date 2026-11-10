from datetime import date, datetime
from decimal import Decimal
from ..db import query, execute, transaction
from ..common import BusinessError, integer, decimal, iso_date, business_today


def create_order(customer_id, employee_id, shipper_id, items, freight='0', order_date=None, required_date=None):
    """All validation/writes are one transaction; product locks follow ascending ID order."""
    employee_id = integer(employee_id, '员工', 1)
    shipper_id = integer(shipper_id, '物流公司', 1)
    freight = decimal(freight, '运费', Decimal('9999.99'))
    ordered = iso_date(order_date or business_today().isoformat(), '订单日期', True)
    required = iso_date(required_date, '要求送达日期')
    if required and required < ordered:
        raise BusinessError('要求送达日期不能早于订单日期。')
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise BusinessError('每笔订单需要 1 至 100 条商品明细。')
    lines = {}
    for item in items:
        product_id = integer(item.get('product_id'), '商品编号', 1)
        if product_id in lines:
            raise BusinessError('一笔订单不能重复添加同一商品，请合并数量。')
        lines[product_id] = (integer(item.get('quantity'), '购买数量', 1),
                             decimal(item.get('discount', '0'), '折扣', Decimal('1'), places=6))
    with transaction():
        customer = query('SELECT * FROM Customers WHERE CustomerID=%s FOR SHARE', (customer_id,), one=True)
        if not customer:
            raise BusinessError('客户不存在。')
        if not query('SELECT EmployeeID FROM Employees WHERE EmployeeID=%s FOR SHARE', (employee_id,), one=True):
            raise BusinessError('员工不存在。')
        if not query('SELECT ShipperID FROM Shippers WHERE ShipperID=%s FOR SHARE', (shipper_id,), one=True):
            raise BusinessError('物流公司不存在。')
        locked = {}
        # Individual point lookups make lock ordering explicit, independent of an optimizer plan.
        for product_id in sorted(lines):
            product = query('SELECT ProductID,ProductName,UnitPrice,UnitsInStock,Discontinued FROM Products WHERE ProductID=%s FOR UPDATE', (product_id,), one=True)
            if not product or str(product['Discontinued']) != '0' or product['UnitPrice'] is None:
                raise BusinessError(f'商品 {product_id} 不存在、已停用或未定价。')
            quantity, discount = lines[product_id]
            if (product['UnitsInStock'] or 0) < quantity:
                raise BusinessError(f'商品「{product["ProductName"]}」库存不足，当前库存 {product["UnitsInStock"] or 0}。')
            locked[product_id] = product
        order_id = execute('''INSERT INTO Orders (CustomerID,EmployeeID,OrderDate,RequiredDate,ShipVia,Freight,
            ShipName,ShipAddress,ShipCity,ShipRegion,ShipPostalCode,ShipCountry)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (customer_id,employee_id,ordered,required,shipper_id,freight,customer['CompanyName'],customer['Address'],
             customer['City'],customer['Region'],customer['PostalCode'],customer['Country']))
        for product_id in sorted(lines):
            quantity, discount = lines[product_id]
            price = locked[product_id]['UnitPrice']  # PyMySQL returns MySQL DECIMAL as Decimal.
            execute('INSERT INTO `Order Details` (OrderID,ProductID,UnitPrice,Quantity,Discount) VALUES (%s,%s,%s,%s,%s)',
                    (order_id,product_id,price,quantity,discount))
            execute('UPDATE Products SET UnitsInStock=UnitsInStock-%s WHERE ProductID=%s', (quantity,product_id))
        execute("INSERT INTO app_order_meta (order_id,status) VALUES (%s,'active')", (order_id,))
    return order_id


def cancel_order(order_id):
    with transaction():
        order = query('SELECT OrderID FROM Orders WHERE OrderID=%s FOR UPDATE', (order_id,), one=True)
        meta = query('SELECT status FROM app_order_meta WHERE order_id=%s FOR UPDATE', (order_id,), one=True)
        if not order or not meta:
            raise BusinessError('仅允许取消本系统创建的订单；Northwind 历史订单只读。')
        if meta['status'] != 'active':
            raise BusinessError('订单已取消，不能重复取消。')
        details = query('SELECT ProductID,Quantity FROM `Order Details` WHERE OrderID=%s ORDER BY ProductID', (order_id,))
        for line in details:
            product = query('SELECT ProductID FROM Products WHERE ProductID=%s FOR UPDATE', (line['ProductID'],), one=True)
            if not product:
                raise BusinessError('订单关联的商品不存在，无法恢复库存。')
        for line in details:
            execute('UPDATE Products SET UnitsInStock=UnitsInStock+%s WHERE ProductID=%s', (line['Quantity'],line['ProductID']))
        execute("UPDATE app_order_meta SET status='cancelled',cancelled_at=CURRENT_TIMESTAMP WHERE order_id=%s", (order_id,))
