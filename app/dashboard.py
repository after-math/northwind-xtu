from flask import Blueprint, render_template, jsonify
from .db import query
from .services.analytics import sales_data, stock_alerts

bp = Blueprint('dashboard', __name__)


@bp.get('/health')
def health():
    query('SELECT 1 AS ok', one=True)
    return jsonify(status='ok', database='mysql')


@bp.get('/dashboard')
def index():
    totals = query('''SELECT (SELECT COUNT(*) FROM Products) AS products,
        (SELECT COUNT(*) FROM Customers) AS customers,
        (SELECT COUNT(*) FROM v_order_amounts) AS orders,
        (SELECT COALESCE(SUM(SalesAmount),0) FROM v_order_amounts) AS sales,
        (SELECT MIN(LEFT(OrderDate,10)) FROM Orders) AS first_date,
        (SELECT MAX(LEFT(OrderDate,10)) FROM Orders) AS last_date''', one=True)
    recent = query('''SELECT o.OrderID,o.OrderDate,c.CompanyName,v.SalesAmount,m.status,
        CASE WHEN m.order_id IS NULL THEN 1 ELSE 0 END AS historical
        FROM Orders o LEFT JOIN Customers c ON c.CustomerID=o.CustomerID
        LEFT JOIN v_order_amounts v ON v.OrderID=o.OrderID LEFT JOIN app_order_meta m ON m.order_id=o.OrderID
        ORDER BY o.OrderID DESC LIMIT 6''')
    return render_template('dashboard.html', totals=totals, recent=recent,
                           alerts=stock_alerts(), charts=sales_data())
