import os
import secrets
from flask_talisman import Talisman
from config import Config


def load_secret_key():
    """Возвращает SECRET_KEY: env → файл → новый."""
    key = os.environ.get('FLASK_SECRET_KEY')
    if key:
        return key
    if os.path.exists(Config.SECRET_KEY_FILE):
        try:
            with open(Config.SECRET_KEY_FILE, 'r', encoding='utf-8') as f:
                saved = f.read().strip()
                if saved:
                    return saved
        except Exception:
            pass
    key = secrets.token_hex(32)
    try:
        with open(Config.SECRET_KEY_FILE, 'w', encoding='utf-8') as f:
            f.write(key)
        try:
            os.chmod(Config.SECRET_KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass
    return key


def init_talisman(app):
    """Настраивает security-заголовки."""
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self'",
        'img-src': "'self' data:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'",
    }
    Talisman(
        app,
        force_https=not Config.IS_DEV,
        force_https_permanent=True,
        strict_transport_security=not Config.IS_DEV,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=True,
        content_security_policy=csp,
        content_security_policy_report_only=False,
        frame_options='DENY',
        frame_options_allow_from=None,
        x_content_type_options=True,
        x_xss_protection=True,
        referrer_policy='strict-origin-when-cross-origin',
        session_cookie_secure=not Config.IS_DEV,
        session_cookie_http_only=True,
        session_cookie_samesite='Lax',
    )