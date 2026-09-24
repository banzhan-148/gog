from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash

from extensions import limiter
from config import Config
from db import q
from utils import clean_text, current_user, log_action

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit(Config.LOGIN_LIMIT, methods=['POST'])
def login():
    if current_user():
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = clean_text(request.form.get('username'), 64)
        password = request.form.get('password') or ''
        u = q('SELECT * FROM users WHERE username = ?', (username,), one=True)
        if u and u['is_active'] and check_password_hash(u['password_hash'], password):
            session.clear()
            session['user_id'] = u['id']
            session.permanent = True
            log_action('Вход в систему', 'user', u['id'])
            return redirect(url_for('dashboard.index'))
        flash('Неверный логин или пароль', 'error')
    return render_template('login.html')


@bp.route('/logout')
def logout():
    u = current_user()
    if u:
        log_action('Выход из системы', 'user', u['id'])
    session.clear()
    return redirect(url_for('auth.login'))