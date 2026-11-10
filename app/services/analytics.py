from ..db import query


def sales_data(start=None, end=None):
    clauses, args = [], []
    if start:
        clauses.append('v.OrderDate >= %s')
        args.append(start)
    if end:
        clauses.append('v.OrderDate < %s')
        args.append(end)
    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    months = query("SELECT LEFT(v.OrderDate,7) AS month, SUM(v.SalesAmount) AS amount, COUNT(*) AS orders FROM v_order_amounts v" + where + ' GROUP BY month ORDER BY month', args)
    valid = "(m.order_id IS NULL OR m.status='active')"
    if start:
        valid += ' AND o.OrderDate >= %s'
    if end:
        valid += ' AND o.OrderDate < %s'
    line = 'd.UnitPrice*d.Quantity*(1-CAST(d.Discount AS DECIMAL(10,6)))'
    categories = query(f'''SELECT c.CategoryID,c.CategoryName, SUM({line}) AS amount, SUM(d.Quantity) AS quantity
        FROM Categories c JOIN Products p ON p.CategoryID=c.CategoryID
        JOIN `Order Details` d ON d.ProductID=p.ProductID JOIN Orders o ON o.OrderID=d.OrderID
        LEFT JOIN app_order_meta m ON m.order_id=o.OrderID WHERE {valid}
        GROUP BY c.CategoryID,c.CategoryName ORDER BY amount DESC''', args)
    products = query(f'''SELECT p.ProductID,p.ProductName,SUM(d.Quantity) AS quantity,SUM({line}) AS amount
        FROM Products p JOIN `Order Details` d ON d.ProductID=p.ProductID
        JOIN Orders o ON o.OrderID=d.OrderID LEFT JOIN app_order_meta m ON m.order_id=o.OrderID
        WHERE {valid} GROUP BY p.ProductID,p.ProductName ORDER BY amount DESC LIMIT 10''', args)
    volume = query(f'''SELECT p.ProductID,p.ProductName,SUM(d.Quantity) AS quantity,SUM({line}) AS amount
        FROM Products p JOIN `Order Details` d ON d.ProductID=p.ProductID
        JOIN Orders o ON o.OrderID=d.OrderID LEFT JOIN app_order_meta m ON m.order_id=o.OrderID
        WHERE {valid} GROUP BY p.ProductID,p.ProductName ORDER BY quantity DESC LIMIT 10''', args)
    customers = query('''SELECT c.CustomerID,c.CompanyName,COUNT(*) AS orders,SUM(v.SalesAmount) AS amount
        FROM Customers c JOIN v_order_amounts v ON v.CustomerID=c.CustomerID''' + where +
        ' GROUP BY c.CustomerID,c.CompanyName ORDER BY amount DESC LIMIT 10', args)
    return dict(months=months, categories=categories, top_products=products, volume=volume, top_customers=customers)


def stock_alerts():
    return query('''SELECT p.*,c.CategoryName FROM Products p LEFT JOIN Categories c ON c.CategoryID=p.CategoryID
        WHERE p.Discontinued='0' AND COALESCE(p.UnitsInStock,0)<=COALESCE(p.ReorderLevel,0)
        ORDER BY p.UnitsInStock,p.ProductID''')
