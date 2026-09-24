import os
import re
import shutil
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from config import Config
from db import q, execute
from utils import login_required, role_required, clean_text, log_action

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    users = q("SELECT * FROM users ORDER BY username")
    logs = q("""SELECT l.*, u.username FROM audit_log l
                LEFT JOIN users u ON u.id=l.user_id
                ORDER BY l.created_at DESC LIMIT 200""")
    return render_template('admin.html', users=users, logs=logs)


@bp.route('/users/new', methods=['POST'])
@login_required
@role_required('admin')
def user_new():
    username = clean_text(request.form.get('username'), 64)
    full_name = clean_text(request.form.get('full_name'), 128)
    password = request.form.get('password') or ''
    role = clean_text(request.form.get('role'), 32)

    if not username or len(username) < 3:
        flash('Логин должен содержать минимум 3 символа', 'error')
        return redirect(url_for('admin.index'))
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', username):
        flash('Логин: только латиница, цифры, _ . -', 'error')
        return redirect(url_for('admin.index'))
    if not full_name:
        flash('ФИО обязательно', 'error')
        return redirect(url_for('admin.index'))
    if len(password) < 6:
        flash('Пароль должен содержать минимум 6 символов', 'error')
        return redirect(url_for('admin.index'))
    if role not in Config.ROLES:
        flash('Некорректная роль', 'error')
        return redirect(url_for('admin.index'))

    exists = q("SELECT id FROM users WHERE username=?", (username,), one=True)
    if exists:
        flash('Пользователь с таким логином уже существует', 'error')
        return redirect(url_for('admin.index'))

    uid = execute("INSERT INTO users (username, full_name, password_hash, role) "
                  "VALUES (?, ?, ?, ?)",
                  (username, full_name,
                   generate_password_hash(password), role))
    log_action(f'Создан пользователь {username} ({role})', 'user', uid)
    flash('Пользователь создан', 'success')
    return redirect(url_for('admin.index'))


@bp.route('/users/<int:uid>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def user_toggle(uid):
    u = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if u and u['username'] != 'admin':
        execute("UPDATE users SET is_active=? WHERE id=?",
                (0 if u['is_active'] else 1, uid))
        log_action(f'Изменена активность {u["username"]}', 'user', uid)
        flash('Статус пользователя изменён', 'success')
    else:
        flash('Нельзя заблокировать главного администратора', 'warning')
    return redirect(url_for('admin.index'))


@bp.route('/users/<int:uid>/reset', methods=['POST'])
@login_required
@role_required('admin')
def user_reset(uid):
    u = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    password = request.form.get('password') or ''
    if len(password) < 6:
        flash('Пароль должен содержать минимум 6 символов', 'error')
        return redirect(url_for('admin.index'))
    if u:
        execute("UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(password), uid))
        log_action(f'Сброс пароля {u["username"]}', 'user', uid)
        flash('Пароль изменён', 'success')
    return redirect(url_for('admin.index'))


@bp.route('/backup', methods=['POST'])
@login_required
@role_required('admin')
def backup():
    os.makedirs(Config.BACKUPS_DIR, exist_ok=True)
    dst = os.path.join(
        Config.BACKUPS_DIR,
        f'atelier_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy2(Config.DATABASE, dst)
    log_action(f'Резервная копия: {os.path.basename(dst)}', 'system', None)
    flash(f'Резервная копия создана: {os.path.basename(dst)}', 'success')
    return redirect(url_for('admin.index'))