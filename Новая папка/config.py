import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IS_DEV = os.environ.get('FLASK_ENV', 'development') != 'production'


class Config:
    SECRET_KEY_FILE = os.path.join(BASE_DIR, '.secret_key')
    DATABASE = os.path.join(BASE_DIR, 'atelier.db')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    BACKUPS_DIR = os.path.join(BASE_DIR, 'backups')

    # Сессия
    PERMANENT_SESSION_LIFETIME_SECONDS = 8 * 60 * 60   # 8 часов

    # Cookies
    SESSION_COOKIE_SECURE = not IS_DEV
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CSRF (в СЕКУНДАХ!)
    WTF_CSRF_TIME_LIMIT = 8 * 60 * 60
    WTF_CSRF_SSL_STRICT = not IS_DEV

    # Лимиты запросов
    MAX_CONTENT_LENGTH = 1024 * 1024
    LOGIN_LIMIT = '10 per minute'
    API_LIMIT = '60 per minute'
    DEFAULT_LIMIT = '300 per minute'

    # Режим
    IS_DEV = IS_DEV

    # Константы предметной области
    ORDER_STATUSES = ['принят', 'в работе', 'на примерке', 'готов', 'выдан', 'отменён']
    WORK_TYPES = ['пошив', 'ремонт', 'подгонка']
    ROLES = ['admin', 'receptionist', 'worker', 'director']