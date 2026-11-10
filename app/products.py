from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import query, execute, transaction
from .common import BusinessError, text, integer, decimal, require_row, page_query, like

bp = Blueprint('products', __name__, url_prefix='/products')


def options():
    return dict(categories=query('SELECT CategoryID,CategoryName FROM Categories ORDER BY CategoryID'),
                suppliers=query('SELECT SupplierID,CompanyName FROM Suppliers ORDER BY SupplierID'))


def values(form):
    data = dict(ProductName=text(form, 'ProductName', '商品名称', True),
                CategoryID=integer(form.get('CategoryID'), '分类', 1),
                SupplierID=integer(form.get('SupplierID'), '供应商', 1),
                QuantityPerUnit=text(form, 'QuantityPerUnit', '包装规格'),
                UnitPrice=decimal(form.get('UnitPrice'), '单价'),
                UnitsInStock=integer(form.get('UnitsInStock'), '库存'),
                ReorderLevel=integer(form.get('ReorderLevel', '0'), '预警阈值'),
                Discontinued='1' if form.get('Discontinued') == '1' else '0')
    if not query('SELECT CategoryID FROM Categories WHERE CategoryID=%s', (data['CategoryID'],), one=True):
        raise BusinessError('所选分类不存在。')
    if not query('SELECT SupplierID FROM Suppliers WHERE SupplierID=%s', (data['SupplierID'],), one=True):
        raise BusinessError('所选供应商不存在。')
    return data


@bp.get('/')
def index():
    parts, args = [], []
    q = request.args.get('q', '').strip()
    if q:
        parts.append("p.ProductName LIKE %s ESCAPE '!'")
        args.append(like(q))
    for key in ('CategoryID', 'SupplierID'):
        if request.args.get(key):
            parts.append(f'p.{key}=%s')
            args.append(integer(request.args[key], key, 1))
    if request.args.get('low_stock') == '1':
        parts.append("p.Discontinued='0' AND COALESCE(p.UnitsInStock,0)<=COALESCE(p.ReorderLevel,0)")
    where = ' WHERE ' + ' AND '.join(parts) if parts else ''
    rows, pager = page_query('SELECT COUNT(*) AS n FROM Products p' + where,
        '''SELECT p.*,c.CategoryName,s.CompanyName FROM Products p
        LEFT JOIN Categories c ON c.CategoryID=p.CategoryID LEFT JOIN Suppliers s ON s.SupplierID=p.SupplierID'''
        + where + ' ORDER BY p.ProductID', args)
    return render_template('products/index.html', rows=rows, pager=pager, **options())


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
def edit(product_id=None):
    product = require_row('SELECT * FROM Products WHERE ProductID=%s', (product_id,)) if product_id else {}
    error = None
    if request.method == 'POST':
        try:
            data = values(request.form)
            with transaction():
                if product_id:
                    locked = require_row('SELECT UnitsInStock FROM Products WHERE ProductID=%s FOR UPDATE', (product_id,))
                    if str(locked['UnitsInStock'] or 0) != request.form.get('original_stock'):
                        raise BusinessError('库存已被其他操作更新，请重新打开商品后编辑。')
                    execute('UPDATE Products SET ProductName=%s,CategoryID=%s,SupplierID=%s,QuantityPerUnit=%s,UnitPrice=%s,UnitsInStock=%s,ReorderLevel=%s,Discontinued=%s WHERE ProductID=%s', (*data.values(), product_id))
                else:
                    execute('INSERT INTO Products (ProductName,CategoryID,SupplierID,QuantityPerUnit,UnitPrice,UnitsInStock,ReorderLevel,Discontinued) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', tuple(data.values()))
            flash('商品已保存。', 'success')
            return redirect(url_for('products.index'))
        except BusinessError as exc:
            error = str(exc)
            product = request.form.to_dict()
    return render_template('products/form.html', product=product, product_id=product_id, error=error, **options()), (400 if error else 200)


@bp.post('/<int:product_id>/delete')
def delete(product_id):
    with transaction():
        require_row('SELECT ProductID FROM Products WHERE ProductID=%s FOR UPDATE', (product_id,))
        related = query('SELECT 1 FROM `Order Details` WHERE ProductID=%s LIMIT 1', (product_id,), one=True)
        if related:
            execute("UPDATE Products SET Discontinued='1' WHERE ProductID=%s", (product_id,))
            flash('商品有历史订单记录，已将其停用。', 'success')
        else:
            execute('DELETE FROM Products WHERE ProductID=%s', (product_id,))
            flash('商品已删除。', 'success')
    return redirect(url_for('products.index'))
