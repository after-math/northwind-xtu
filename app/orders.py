from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import query
from .common import BusinessError, integer, iso_date, require_row, page_query, business_today
from .services.order_service import create_order, cancel_order

bp = Blueprint('orders', __name__, url_prefix='/orders')


def options():
    return dict(customers=query('SELECT CustomerID,CompanyName FROM Customers ORDER BY CompanyName'),
                employees=query("SELECT EmployeeID,CONCAT(FirstName,' ',LastName) AS name FROM Employees ORDER BY EmployeeID"),
                shippers=query('SELECT ShipperID,CompanyName FROM Shippers ORDER BY ShipperID'),
                products=query("SELECT ProductID,ProductName,UnitPrice,UnitsInStock FROM Products WHERE Discontinued='0' AND UnitPrice IS NOT NULL ORDER BY ProductName"))


@bp.get('/')
def index():
    clauses, args = [], []
    if request.args.get('order_id'):
        clauses.append('o.OrderID=%s')
        args.append(integer(request.args['order_id'], '订单编号', 1))
    if request.args.get('customer_id'):
        clauses.append('o.CustomerID=%s')
        args.append(request.args['customer_id'])
    start = iso_date(request.args.get('start'), '起始日期')
    end = iso_date(request.args.get('end'), '结束日期')
    if start and end and start > end:
        raise BusinessError('起始日期不能晚于结束日期。')
    if start:
        clauses.append('o.OrderDate >= %s')
        args.append(start)
    if end:
        if end >= '9999-12-31':
            raise BusinessError('结束日期超出支持范围。')
        clauses.append('o.OrderDate < %s')
        args.append((date.fromisoformat(end)+timedelta(days=1)).isoformat())
    if request.args.get('status') == 'cancelled':
        clauses.append("m.status='cancelled'")
    elif request.args.get('status') == 'active':
        clauses.append("m.status='active'")
    elif request.args.get('status') == 'historical':
        clauses.append('m.order_id IS NULL')
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    join = ' FROM Orders o LEFT JOIN app_order_meta m ON m.order_id=o.OrderID'
    rows, pager = page_query('SELECT COUNT(*) AS n' + join + where,
        '''SELECT o.OrderID,o.OrderDate,o.Freight,c.CompanyName,m.status,
        CASE WHEN m.order_id IS NULL THEN 1 ELSE 0 END AS historical,
        (SELECT COALESCE(SUM(d.UnitPrice*d.Quantity*(1-CAST(d.Discount AS DECIMAL(10,6)))),0)
        FROM `Order Details` d WHERE d.OrderID=o.OrderID) AS SalesAmount'''
        + join + ' LEFT JOIN Customers c ON c.CustomerID=o.CustomerID' + where + ' ORDER BY o.OrderID DESC', args)
    customers = query('SELECT CustomerID,CompanyName FROM Customers ORDER BY CompanyName')
    return render_template('orders/index.html', rows=rows, pager=pager, customers=customers)


@bp.get('/<int:order_id>')
def detail(order_id):
    order = require_row('''SELECT o.*,c.CompanyName,CONCAT(e.FirstName,' ',e.LastName) AS employee,
        s.CompanyName AS shipper,m.status,m.created_at,m.cancelled_at
        FROM Orders o LEFT JOIN Customers c ON c.CustomerID=o.CustomerID
        LEFT JOIN Employees e ON e.EmployeeID=o.EmployeeID LEFT JOIN Shippers s ON s.ShipperID=o.ShipVia
        LEFT JOIN app_order_meta m ON m.order_id=o.OrderID WHERE o.OrderID=%s''', (order_id,))
    details = query('''SELECT d.*,p.ProductName,CAST(d.Discount AS DECIMAL(10,6)) AS discount_decimal,
        d.UnitPrice*d.Quantity*(1-CAST(d.Discount AS DECIMAL(10,6))) AS amount
        FROM `Order Details` d JOIN Products p ON p.ProductID=d.ProductID WHERE d.OrderID=%s ORDER BY d.ProductID''', (order_id,))
    subtotal = sum((d['amount'] for d in details), Decimal(0))
    return render_template('orders/detail.html', order=order, details=details, subtotal=subtotal,
                           total=subtotal+(order['Freight'] or Decimal(0)))


@bp.route('/new', methods=['GET', 'POST'])
def new():
    error, submitted = None, []
    if request.method == 'POST':
        ids, quantities, discounts = (request.form.getlist(key) for key in ('product_id[]','quantity[]','discount[]'))
        try:
            if len(ids) != len(quantities) or len(ids) != len(discounts):
                raise BusinessError('商品明细字段不完整。')
            submitted = [dict(product_id=p,quantity=q,discount=d) for p,q,d in zip(ids,quantities,discounts)]
            order_id = create_order(request.form.get('customer_id'), request.form.get('employee_id'),
                request.form.get('shipper_id'), submitted, request.form.get('freight','0'),
                request.form.get('order_date'), request.form.get('required_date'))
            flash(f'订单 #{order_id} 已创建，库存已同步扣减。', 'success')
            return redirect(url_for('orders.detail', order_id=order_id))
        except BusinessError as exc:
            error = str(exc)
    return render_template('orders/new.html', error=error, submitted=submitted, today=business_today().isoformat(), **options()), (400 if error else 200)


@bp.post('/<int:order_id>/cancel')
def cancel(order_id):
    cancel_order(order_id)
    flash('订单已取消，库存已恢复；销售统计已同步更新。', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))
