import hmac
import secrets
from decimal import Decimal
from flask import Flask, render_template, request, session, abort, redirect, url_for, flash
import pymysql
from config import Config
from .db import close_db
from .common import BusinessError, page_url


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    key = app.config['SECRET_KEY']
    if not key or len(key) < 32 or key.startswith('replace-'):
        raise RuntimeError('请在 .env 中设置至少 32 位的随机 SECRET_KEY。')
    app.teardown_appcontext(close_db)

    from . import auth, dashboard, products, customers, orders, suppliers, reports, public
    for module in (auth, dashboard, products, customers, orders, suppliers, reports, public):
        app.register_blueprint(module.bp)

    @app.before_request
    def protect():
        if request.endpoint == 'static':
            return None
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            expected = session.get('csrf_token', '')
            supplied = request.form.get('csrf_token', '')
            if not expected or not supplied.isascii() or not hmac.compare_digest(expected, supplied):
                abort(400, description='表单已过期，请刷新页面后重试。')
        if request.endpoint not in {'auth.login', 'dashboard.health', 'public.home', 'public.robots', 'public.sitemap'} and not session.get('user_id'):
            return redirect(url_for('auth.login', next=request.full_path))

    @app.context_processor
    def helpers():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return dict(csrf_token=lambda: session['csrf_token'], page_url=page_url)

    @app.template_filter('money')
    def money(value):
        return f'{Decimal(str(value or 0)):,.2f}'

    @app.template_filter('day')
    def day(value):
        return str(value)[:10] if value else '—'

    @app.errorhandler(BusinessError)
    def invalid(error):
        return render_template('errors/error.html', code=400, message=str(error)), 400

    @app.errorhandler(pymysql.err.IntegrityError)
    def integrity(error):
        app.logger.warning('Database integrity error code=%s', error.args[0])
        return render_template('errors/error.html', code=409,
                               message='数据存在关联、编号冲突或约束冲突，请刷新后检查输入。'), 409

    @app.errorhandler(pymysql.err.OperationalError)
    def database_unavailable(error):
        app.logger.warning('Database operational error code=%s', error.args[0])
        return render_template('errors/error.html', code=503,
                               message='数据库暂时无法访问，请检查数据库服务、连接配置或稍后重试。'), 503

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def http_error(error):
        messages = {404: '页面或记录不存在。', 405: '该操作不支持此请求方式。', 413: '提交的表单内容过大。'}
        return render_template('errors/error.html', code=error.code,
                               message=messages.get(error.code, error.description)), error.code

    @app.errorhandler(500)
    def internal(error):
        return render_template('errors/error.html', code=500,
                               message='操作未完成，请稍后重试或联系管理员。'), 500

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
            if request.endpoint != 'public.home' or response.status_code != 200:
                response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response

    return app
