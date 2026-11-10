from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import pytest
from app.db import query,execute
from app.common import BusinessError
from app.services.order_service import create_order,cancel_order


def order(items=None,**kwargs):
    return create_order('ALFKI',1,1,items or [dict(product_id=1,quantity=2,discount='0.1')],**kwargs)


def test_import_source_counts_and_snapshot(context):
    for table,count in [('Products',77),('Customers',93),('Orders',830),('Order Details',2155),('Categories',8),('Suppliers',29)]:
        assert query(f'SELECT COUNT(*) AS n FROM `{table}`',one=True)['n']==count
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==39
    assert query('SELECT MIN(OrderDate) AS first,MAX(OrderDate) AS last FROM Orders',one=True)['first'].startswith('2016')


def test_views_and_extensions_are_repeatable(context):
    from scripts.init_db import statements
    from config import BASE_DIR
    for sql in statements((BASE_DIR/'sql/extensions.sql').read_text()):
        execute(sql)
    assert query('SELECT COUNT(*) AS n FROM v_order_amounts',one=True)['n']==830
    total=query('SELECT SUM(SalesAmount) AS s FROM v_order_amounts',one=True)['s']
    assert total==query('SELECT SUM(SalesAmount) AS s FROM v_product_sales',one=True)['s']


def test_login_logout_csrf_and_auth(app,context):
    client=app.test_client()
    assert client.get('/products/').status_code==302
    assert client.get('/dashboard').status_code==302
    client.get('/login')
    with client.session_transaction() as s:
        token=s['csrf_token']
    assert client.post('/login',data={'username':'tester','password':'bad','csrf_token':token}).status_code==401
    assert client.post('/login',data={'username':'tester','password':'integration-test-password','csrf_token':token}).status_code==302
    assert client.get('/dashboard').status_code==200
    assert client.post('/logout').status_code==400
    with client.session_transaction() as s:
        token=s['csrf_token']
    assert client.post('/logout',data={'csrf_token':token}).status_code==302
    assert client.get('/orders/').status_code==302


def test_all_pages_render_real_data(client):
    for path in ['/', '/dashboard', '/products/','/products/new','/products/1/edit','/customers/','/customers/new',
                 '/customers/ALFKI','/customers/ALFKI/edit','/orders/','/orders/10248','/orders/new',
                 '/partners/categories','/partners/categories/new','/partners/categories/1/edit',
                 '/partners/suppliers','/partners/suppliers/new','/partners/suppliers/1/edit','/reports/',
                 '/reports/?start=2016-07-01&end=2016-07-31','/orders/?start=2016-07-01&end=2016-07-31',
                 '/products/?q=Chai&CategoryID=1&SupplierID=1','/customers/?country=Germany&q=Alfred',
                 '/orders/?status=historical','/reports/?start=2090-01-01']:
        response=client.get(path)
        assert response.status_code==200,(path,response.data[:200])
    assert b'Chai' in client.get('/products/?q=Chai').data
    assert client.get('/does-not-exist').status_code==404


def test_product_crud_and_validation(client):
    data=dict(ProductName='Test product',CategoryID=1,SupplierID=1,QuantityPerUnit='box',UnitPrice='5.50',UnitsInStock=8,ReorderLevel=2,Discontinued='0',csrf_token='test-csrf-token')
    assert client.post('/products/new',data={**data,'UnitPrice':'-1'}).status_code==400
    assert client.post('/products/new',data={**data,'CategoryID':9999}).status_code==400
    assert client.post('/products/new',data=data).status_code==302
    product=query("SELECT * FROM Products WHERE ProductName='Test product'",one=True)
    pid=product['ProductID']
    assert client.post(f'/products/{pid}/edit',data={**data,'UnitPrice':'7.25','original_stock':'8'}).status_code==302
    assert query('SELECT UnitPrice FROM Products WHERE ProductID=%s',(pid,),one=True)['UnitPrice']==Decimal('7.25')
    assert client.post(f'/products/{pid}/edit',data={**data,'original_stock':'7'}).status_code==400
    assert client.post(f'/products/{pid}/delete',data={'csrf_token':'test-csrf-token'}).status_code==302
    assert not query('SELECT * FROM Products WHERE ProductID=%s',(pid,),one=True)


def test_customer_and_partner_crud(client):
    csrf={'csrf_token':'test-csrf-token'}
    assert client.post('/customers/new',data={**csrf,'CompanyName':'Test customer','Country':'China'}).status_code==302
    cid=query("SELECT CustomerID FROM Customers WHERE CompanyName='Test customer'",one=True)['CustomerID']
    assert len(cid)==5
    assert client.post(f'/customers/{cid}/edit',data={**csrf,'CompanyName':'Updated customer'}).status_code==302
    assert client.post(f'/customers/{cid}/delete',data=csrf).status_code==302
    assert client.post('/customers/ALFKI/delete',data=csrf).status_code==400
    for kind,table,pk,field in [('categories','Categories','CategoryID','CategoryName'),('suppliers','Suppliers','SupplierID','CompanyName')]:
        assert client.post(f'/partners/{kind}/new',data={**csrf,field:'Test partner'}).status_code==302
        rid=query(f'SELECT {pk} AS id FROM {table} WHERE {field}=%s',('Test partner',),one=True)['id']
        assert client.post(f'/partners/{kind}/{rid}/edit',data={**csrf,field:'Updated partner'}).status_code==302
        assert client.post(f'/partners/{kind}/{rid}/delete',data=csrf).status_code==302
        assert client.post(f'/partners/{kind}/1/delete',data=csrf).status_code==400


def test_create_multiline_snapshot_and_cancel(context):
    before=query('SELECT SUM(SalesAmount) AS s FROM v_order_amounts',one=True)['s']
    oid=order([dict(product_id=2,quantity=3,discount='0'),dict(product_id=1,quantity=2,discount='0.1')],freight='8.50')
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==37
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=2',one=True)['UnitsInStock']==14
    assert query('SELECT SalesAmount FROM v_order_amounts WHERE OrderID=%s',(oid,),one=True)['SalesAmount']==Decimal('89.40')
    # Changing a product price must not change the historic transaction price.
    price=query('SELECT UnitPrice FROM Products WHERE ProductID=1',one=True)['UnitPrice']
    execute('UPDATE Products SET UnitPrice=99 WHERE ProductID=1')
    try:
        assert query('SELECT UnitPrice FROM `Order Details` WHERE OrderID=%s AND ProductID=1',(oid,),one=True)['UnitPrice']==price
    finally:
        execute('UPDATE Products SET UnitPrice=%s WHERE ProductID=1',(price,))
    cancel_order(oid)
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==39
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=2',one=True)['UnitsInStock']==17
    assert query('SELECT SUM(SalesAmount) AS s FROM v_order_amounts',one=True)['s']==before
    assert query('SELECT SUM(SalesAmount) AS s FROM v_product_sales',one=True)['s']==before
    with pytest.raises(BusinessError):
        cancel_order(oid)
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==39


@pytest.mark.parametrize('items',[
    [dict(product_id=1,quantity=40,discount='0')],
    [dict(product_id=1,quantity=1),dict(product_id=1,quantity=1)],
    [dict(product_id=5,quantity=1)],
    [dict(product_id=9999,quantity=1)],
    [dict(product_id=1,quantity=0)],
    [dict(product_id=1,quantity=1,discount='1.1')],
    [dict(product_id=1,quantity=1,discount='NaN')],
])
def test_invalid_order_leaves_no_changes(context,items):
    with pytest.raises(BusinessError):
        order(items)
    assert query('SELECT COUNT(*) AS n FROM Orders',one=True)['n']==830
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==39


def test_failure_after_inventory_write_rolls_back(context,monkeypatch):
    from app.services import order_service
    original=order_service.execute
    def fail(sql,args=()):
        if sql.startswith('INSERT INTO app_order_meta'):
            raise RuntimeError('injected failure after stock update')
        return original(sql,args)
    monkeypatch.setattr(order_service,'execute',fail)
    with pytest.raises(RuntimeError):
        order()
    assert query('SELECT COUNT(*) AS n FROM Orders',one=True)['n']==830
    assert query('SELECT COUNT(*) AS n FROM `Order Details`',one=True)['n']==2155
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==39


def test_historical_order_cannot_cancel(context):
    with pytest.raises(BusinessError):
        cancel_order(10248)
    assert query('SELECT COUNT(*) AS n FROM app_order_meta',one=True)['n']==0


def test_parallel_purchase_prevents_overselling(app,context):
    execute('UPDATE Products SET UnitsInStock=1 WHERE ProductID=1')
    barrier=Barrier(2)
    def buy():
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                return ('ok',order([dict(product_id=1,quantity=1)]))
            except BusinessError:
                return ('insufficient',None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:buy(),range(2)))
    assert sorted(x[0] for x in results)==['insufficient','ok']
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==0


def test_parallel_cancellation_restores_once(app,context):
    oid=order()
    barrier=Barrier(2)
    def cancel():
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                cancel_order(oid)
                return 'ok'
            except BusinessError:
                return 'already'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:cancel(),range(2)))
    assert sorted(results)==['already','ok']
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==39


def test_order_form_and_csrf(client):
    data={'csrf_token':'test-csrf-token','customer_id':'ALFKI','employee_id':'1','shipper_id':'1',
          'product_id[]':['1','2'],'quantity[]':['1','2'],'discount[]':['0','0.05'],'freight':'2.50','order_date':'2026-11-10'}
    assert client.post('/orders/new',data={**data,'csrf_token':'bad'}).status_code==400
    response=client.post('/orders/new',data=data)
    assert response.status_code==302
    oid=int(response.headers['Location'].rsplit('/',1)[-1])
    assert client.get(response.headers['Location']).status_code==200
    assert client.post(f'/orders/{oid}/cancel',data={'csrf_token':'test-csrf-token'}).status_code==302
    assert client.get(response.headers['Location']).status_code==200
    assert client.post(f'/orders/{oid}/cancel',data={'csrf_token':'test-csrf-token'}).status_code==400


def test_related_product_is_disabled(client):
    original=query('SELECT Discontinued FROM Products WHERE ProductID=1',one=True)['Discontinued']
    try:
        assert client.post('/products/1/delete',data={'csrf_token':'test-csrf-token'}).status_code==302
        assert query('SELECT Discontinued FROM Products WHERE ProductID=1',one=True)['Discontinued']=='1'
        assert query('SELECT COUNT(*) AS n FROM `Order Details` WHERE ProductID=1',one=True)['n']>0
    finally:
        execute('UPDATE Products SET Discontinued=%s WHERE ProductID=1',(original,))


def test_cancel_failure_after_restore_rolls_back(context,monkeypatch):
    from app.services import order_service
    oid=order()
    original=order_service.execute
    def fail(sql,args=()):
        if sql.startswith('UPDATE app_order_meta'):
            raise RuntimeError('injected failure after stock restoration')
        return original(sql,args)
    monkeypatch.setattr(order_service,'execute',fail)
    with pytest.raises(RuntimeError):
        cancel_order(oid)
    assert query('SELECT UnitsInStock FROM Products WHERE ProductID=1',one=True)['UnitsInStock']==37
    assert query('SELECT status FROM app_order_meta WHERE order_id=%s',(oid,),one=True)['status']=='active'


def test_non_ascii_csrf_is_rejected(client):
    assert client.post('/logout',data={'csrf_token':'非法值'}).status_code==400


@pytest.mark.parametrize('args',[
    ('MISSING',1,1),('ALFKI',9999,1),('ALFKI',1,9999)
])
def test_invalid_foreign_reference(context,args):
    with pytest.raises(BusinessError):
        create_order(*args,[dict(product_id=1,quantity=1)])
    assert query('SELECT COUNT(*) AS n FROM Orders',one=True)['n']==830


def test_login_redirect_stays_local(app,context):
    for target,expected in [('//example.invalid','/dashboard'),('/\\example.invalid','/dashboard'),('https://example.invalid','/dashboard'),('/\nexample.invalid','/dashboard'),('/products/','/products/')]:
        client=app.test_client()
        client.get('/login')
        with client.session_transaction() as s:
            token=s['csrf_token']
        response=client.post('/login',query_string={'next':target},data={
            'username':'tester','password':'integration-test-password','csrf_token':token})
        assert response.status_code==302
        assert response.headers['Location']==expected
