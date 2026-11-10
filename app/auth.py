from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import check_password_hash
from .db import query

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard.index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = query('SELECT id,username,password_hash FROM admin_user WHERE username=%s', (username,), one=True)
        if user and check_password_hash(user['password_hash'], request.form.get('password', '')):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            target = request.args.get('next', '')
            if not target.startswith('/') or target.startswith('//') or chr(92) in target or any(ord(char)<32 for char in target):
                target = url_for('dashboard.index')
            return redirect(target)
        error = '账号或密码不正确。'
    return render_template('login.html', error=error), (401 if error else 200)


@bp.post('/logout')
def logout():
    session.clear()
    flash('已安全退出。', 'success')
    return redirect(url_for('auth.login'))
