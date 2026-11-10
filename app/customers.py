import secrets
import string
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import query, execute, transaction
from .common import BusinessError, text, require_row, page_query, like

bp = Blueprint('customers', __name__, url_prefix='/customers')
FIELDS = ('CompanyName','ContactName','ContactTitle','Address','City','Region','PostalCode','Country','Phone','Fax')
LABELS = ('公司名称','联系人','职务','地址','城市','地区','邮政编码','国家','电话','传真')


@bp.get('/')
def index():
    clauses, args = [], []
    q, country = request.args.get('q', '').strip(), request.args.get('country', '').strip()
    if q:
        clauses.append("(c.CompanyName LIKE %s ESCAPE '!' OR c.ContactName LIKE %s ESCAPE '!')")
        args += [like(q), like(q)]
    if country:
        clauses.append('c.Country=%s')
        args.append(country)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    rows, pager = page_query('SELECT COUNT(*) AS n FROM Customers c' + where,
        '''SELECT c.*,(SELECT COUNT(*) FROM v_order_amounts v WHERE v.CustomerID=c.CustomerID) AS orders,
        (SELECT COALESCE(SUM(v.SalesAmount),0) FROM v_order_amounts v WHERE v.CustomerID=c.CustomerID) AS spent
        FROM Customers c''' + where + ' ORDER BY c.CustomerID', args)
    countries = query('SELECT DISTINCT Country FROM Customers WHERE Country IS NOT NULL ORDER BY Country')
    return render_template('customers/index.html', rows=rows, pager=pager, countries=countries)


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/<customer_id>/edit', methods=['GET', 'POST'])
def edit(customer_id=None):
    customer = require_row('SELECT * FROM Customers WHERE CustomerID=%s', (customer_id,)) if customer_id else {}
    error = None
    if request.method == 'POST':
        try:
            data = [text(request.form, field, label, required=field=='CompanyName') for field,label in zip(FIELDS,LABELS)]
            with transaction():
                if customer_id:
                    execute('UPDATE Customers SET '+','.join(f'{field}=%s' for field in FIELDS)+' WHERE CustomerID=%s', (*data,customer_id))
                else:
                    # Five-character IDs fit both this actual VARCHAR(255) schema and classic Northwind CHAR(5).
                    # A UNIQUE/PK constraint is the final concurrency guard; a collision is shown as HTTP 409.
                    for _ in range(20):
                        new_id = ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(5))
                        if not query('SELECT CustomerID FROM Customers WHERE CustomerID=%s', (new_id,), one=True):
                            break
                    else:
                        raise BusinessError('暂时无法分配客户编号，请重试。')
                    execute('INSERT INTO Customers (CustomerID,'+','.join(FIELDS)+') VALUES ('+','.join(['%s']*11)+')', (new_id,*data))
            flash('客户已保存。', 'success')
            return redirect(url_for('customers.index'))
        except BusinessError as exc:
            error, customer = str(exc), request.form.to_dict()
    return render_template('customers/form.html', customer=customer, customer_id=customer_id, fields=list(zip(FIELDS,LABELS)), error=error), (400 if error else 200)


@bp.get('/<customer_id>')
def detail(customer_id):
    customer = require_row('SELECT * FROM Customers WHERE CustomerID=%s', (customer_id,))
    rows, pager = page_query('SELECT COUNT(*) AS n FROM Orders WHERE CustomerID=%s',
        '''SELECT o.*,v.SalesAmount,m.status,CASE WHEN m.order_id IS NULL THEN 1 ELSE 0 END AS historical
        FROM Orders o LEFT JOIN v_order_amounts v ON v.OrderID=o.OrderID
        LEFT JOIN app_order_meta m ON m.order_id=o.OrderID WHERE o.CustomerID=%s ORDER BY o.OrderID DESC''', (customer_id,))
    total = query('SELECT COUNT(*) AS orders,COALESCE(SUM(SalesAmount),0) AS spent FROM v_order_amounts WHERE CustomerID=%s', (customer_id,), one=True)
    return render_template('customers/detail.html', customer=customer, rows=rows, pager=pager, total=total)


@bp.post('/<customer_id>/delete')
def delete(customer_id):
    with transaction():
        require_row('SELECT CustomerID FROM Customers WHERE CustomerID=%s FOR UPDATE', (customer_id,))
        if query('SELECT 1 FROM Orders WHERE CustomerID=%s LIMIT 1', (customer_id,), one=True) or query('SELECT 1 FROM CustomerCustomerDemo WHERE CustomerID=%s LIMIT 1', (customer_id,), one=True):
            raise BusinessError('客户已有订单或客户类型关联，不能直接删除。')
        execute('DELETE FROM Customers WHERE CustomerID=%s', (customer_id,))
    flash('客户已删除。', 'success')
    return redirect(url_for('customers.index'))
