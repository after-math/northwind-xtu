"""Website entry points; business data stays behind administrator login."""
from flask import Blueprint, Response, redirect, session, url_for

bp = Blueprint('public', __name__)


@bp.get('/')
def home():
    endpoint = 'dashboard.index' if session.get('user_id') else 'auth.login'
    return redirect(url_for(endpoint))


@bp.get('/robots.txt')
def robots():
    return Response('User-agent: *\nDisallow: /\n', mimetype='text/plain')


@bp.get('/sitemap.xml')
def sitemap():
    return Response('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>\n',
                    mimetype='application/xml')
