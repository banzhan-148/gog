import re
from functools import wraps
from flask import session, redirect, url_for, abort, request
from db import q, execute


# ============================================================
#  ПОЛЬЗОВАТЕЛЬ
# ============================================================
def current_user():
    """Возвращает dict текущего пользователя или None."""
    uid = session.get('user_id')
    if not uid:
        return None
    u = q('SELECT * FROM users WHERE id = ?', (uid,), one=True)
    if not u or not u['is_active']:
        session.pop('user_id', None)
        return None
    return u


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not current_user():
            return redirect(url_for('auth.login', next=request.path))
        return f(*a, **kw)
    return wrapper


def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                return redirect(url_for('auth.login'))
            if roles and u['role'] not in roles:
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco


def has_role(*roles):
    u = current_user()
    return bool(u and u['role'] in roles)


# ============================================================
#  ЖУРНАЛ
# ============================================================
def log_action(action, target=None, target_id=None):
    u = current_user()
    try:
        execute('INSERT INTO audit_log (user_id, action, target, target_id) '
                'VALUES (?, ?, ?, ?)',
                (u['id'] if u else None, action, target, target_id))
    except Exception:
        pass


# ============================================================
#  ВАЛИДАЦИЯ
# ============================================================
def clean_text(value, max_len=500):
    if value is None:
        return ''
    s = str(value).strip()
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    return s[:max_len]


def clean_phone(value):
    if not value:
        return ''
    return re.sub(r'[^\d+\-() ]', '', str(value))[:32]


def clean_email(value):
    if not value:
        return ''
    s = str(value).strip().lower()[:128]
    if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', s):
        return s
    return ''


def safe_float(value, default=0.0, min_val=None, max_val=None):
    try:
        f = float(value if value not in (None, '') else default)
    except (TypeError, ValueError):
        return default
    if min_val is not None and f < min_val:
        return default
    if max_val is not None and f > max_val:
        return default
    return f


def safe_int(value, default=0, min_val=None, max_val=None):
    try:
        i = int(value if value not in (None, '') else default)
    except (TypeError, ValueError):
        return default
    if min_val is not None and i < min_val:
        return default
    if max_val is not None and i > max_val:
        return default
    return i