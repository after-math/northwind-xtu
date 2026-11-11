"""The website opens at login without exposing or connecting to business data."""
from xml.etree import ElementTree

from app import create_app


def test_home_opens_login_without_database(monkeypatch):
    def no_database(*args, **kwargs):
        raise AssertionError('登录入口不应连接数据库')
    monkeypatch.setattr('app.db.connect', no_database)
    app = create_app({'TESTING': True, 'SECRET_KEY': 'public-test-secret-at-least-32-characters'})
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 302
    assert response.headers['Location'] == '/login'
    login = client.get('/', follow_redirects=True)
    assert login.status_code == 200
    assert '管理员登录'.encode() in login.data
    assert b'name="csrf_token"' in login.data
    assert '查看项目介绍'.encode() not in login.data
    assert login.headers['X-Robots-Tag'] == 'noindex, nofollow'
    robots = client.get('/robots.txt')
    assert robots.status_code == 200
    assert b'Disallow: /\n' in robots.data
    sitemap = client.get('/sitemap.xml')
    root = ElementTree.fromstring(sitemap.data)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    assert root.findall('sm:url', ns) == []
    assert client.get('/login').headers['X-Robots-Tag'] == 'noindex, nofollow'
    for path in ['/dashboard', '/products/', '/customers/', '/orders/', '/reports/', '/partners/suppliers']:
        protected = client.get(path)
        assert protected.status_code == 302
        assert protected.headers['Location'].startswith('/login?')


def test_logged_in_visitors_open_dashboard():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'public-test-secret-at-least-32-characters'})
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['username'] = 'tester'
    response = client.get('/')
    assert response.status_code == 302
    assert response.headers['Location'] == '/dashboard'
