"""Public project introduction; business data stays behind administrator login."""
from urllib.parse import urlsplit

from flask import Blueprint, Response, current_app, render_template, request

bp = Blueprint('public', __name__)


def base_url():
    value = current_app.config.get('PUBLIC_BASE_URL') or request.url_root
    parsed = urlsplit(value)
    if (parsed.scheme not in {'http', 'https'} or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {'', '/'}):
        raise RuntimeError('PUBLIC_BASE_URL 必须是完整的网站根地址。')
    return value.rstrip('/')


@bp.get('/')
def home():
    return render_template('public/home.html', canonical_url=base_url() + '/')


@bp.get('/robots.txt')
def robots():
    lines = ['User-agent: *', 'Allow: /$', 'Disallow: /login', 'Disallow: /logout',
             'Disallow: /dashboard', 'Disallow: /products/', 'Disallow: /customers/',
             'Disallow: /orders/', 'Disallow: /partners/', 'Disallow: /reports/',
             'Disallow: /health', 'Sitemap: ' + base_url() + '/sitemap.xml', '']
    return Response('\n'.join(lines), mimetype='text/plain')


@bp.get('/sitemap.xml')
def sitemap():
    return Response(render_template('public/sitemap.xml', homepage=base_url() + '/'),
                    mimetype='application/xml')
