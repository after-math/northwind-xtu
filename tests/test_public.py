"""The indexable introduction must work without exposing or connecting to business data."""
from xml.etree import ElementTree

from app import create_app


def test_public_pages_work_without_database(monkeypatch):
    def no_database(*args, **kwargs):
        raise AssertionError('公开介绍页不应连接数据库')
    monkeypatch.setattr('app.db.connect', no_database)
    app = create_app({'TESTING': True, 'SECRET_KEY': 'public-test-secret-at-least-32-characters',
                      'PUBLIC_BASE_URL': 'https://project.example'})
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert '商品销售及'.encode() in response.data
    assert b'https://project.example/' in response.data
    assert 'X-Robots-Tag' not in response.headers
    robots = client.get('/robots.txt')
    assert robots.status_code == 200
    assert b'Disallow: /orders/' in robots.data
    assert b'Sitemap: https://project.example/sitemap.xml' in robots.data
    sitemap = client.get('/sitemap.xml')
    root = ElementTree.fromstring(sitemap.data)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    assert [n.text for n in root.findall('sm:url/sm:loc', ns)] == ['https://project.example/']
    assert client.get('/login').headers['X-Robots-Tag'] == 'noindex, nofollow'
    for path in ['/dashboard', '/products/', '/customers/', '/orders/', '/reports/', '/partners/suppliers']:
        protected = client.get(path)
        assert protected.status_code == 302
        assert protected.headers['Location'].startswith('/login?')


def test_logged_in_visitors_can_still_view_public_introduction():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'public-test-secret-at-least-32-characters',
                      'PUBLIC_BASE_URL': ''})
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['username'] = 'tester'
    response = client.get('/')
    assert response.status_code == 200
    assert b'project-site' in response.data
    assert b'<aside class="sidebar"' not in response.data
