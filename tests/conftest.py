import os
import sys
import secrets
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import Config,BASE_DIR
from app import create_app
from app.db import connect,query,execute
from scripts.init_db import statements
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    if os.getenv('RUN_MYSQL_TESTS')!='1':
        pytest.skip('设置 RUN_MYSQL_TESTS=1 后在隔离的临时 MySQL 库运行集成测试')
    cfg={key:getattr(Config,key) for key in dir(Config) if key.startswith('DB_')}
    cfg['DB_USER']=os.getenv('TEST_DB_ADMIN_USER','root')
    cfg['DB_PASSWORD']=os.getenv('TEST_DB_ADMIN_PASSWORD') or os.getenv('MYSQL_ROOT_PASSWORD','')
    schema='northwind_test_'+secrets.token_hex(5)
    cfg['DB_NAME']=None
    admin=connect(cfg)
    with admin.cursor() as cursor:
        cursor.execute('SELECT VERSION() AS v')
        assert cursor.fetchone()['v'].startswith('8.0.'), '仅在 MySQL 8.0 上执行'
        cursor.execute(f'CREATE DATABASE `{schema}` CHARACTER SET utf8mb4')
    cfg['DB_NAME']=schema
    try:
        with connect(cfg) as conn,conn.cursor() as cursor:
            for path in [BASE_DIR/'data/northwind.mysql.sql',BASE_DIR/'sql/extensions.sql']:
                for sql in statements(path.read_text()):
                    cursor.execute(sql)
            cursor.execute('INSERT INTO admin_user (username,password_hash) VALUES (%s,%s)',('tester',generate_password_hash('integration-test-password')))
        yield create_app({**cfg,'TESTING':True,'SECRET_KEY':'integration-secret-at-least-32-characters'})
    finally:
        with admin.cursor() as cursor:
            cursor.execute(f'DROP DATABASE `{schema}`')
        admin.close()


@pytest.fixture()
def context(app):
    with app.app_context():
        stocks=query('SELECT ProductID,UnitsInStock FROM Products')
        original_customers={r['CustomerID'] for r in query('SELECT CustomerID FROM Customers')}
        try:
            yield
        finally:
            execute('DELETE FROM `Order Details` WHERE OrderID>=11078')
            execute('DELETE FROM app_order_meta WHERE order_id>=11078')
            execute('DELETE FROM Orders WHERE OrderID>=11078')
            execute('DELETE FROM Products WHERE ProductID>77')
            execute('DELETE FROM Categories WHERE CategoryID>8')
            execute('DELETE FROM Suppliers WHERE SupplierID>29')
            for r in stocks:
                execute('UPDATE Products SET UnitsInStock=%s WHERE ProductID=%s',(r['UnitsInStock'],r['ProductID']))
            for r in query('SELECT CustomerID FROM Customers'):
                if r['CustomerID'] not in original_customers:
                    execute('DELETE FROM Customers WHERE CustomerID=%s',(r['CustomerID'],))


@pytest.fixture()
def client(app,context):
    client=app.test_client()
    with client.session_transaction() as session:
        session['user_id']=1
        session['username']='tester'
        session['csrf_token']='test-csrf-token'
    return client
