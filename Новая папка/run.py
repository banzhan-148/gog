import os
import traceback
from datetime import timedelta

from flask import Flask, render_template

from config import Config
from extensions import csrf, limiter
from db import close_db, init_db
from security import load_secret_key, init_talisman
from flask_wtf.csrf import CSRFError


def create_app():
    app = Flask(
        __name__,
        static_folder=Config.STATIC_DIR,
        template_folder=Config.TEMPLATES_DIR,
    )

    app.secret_key = load_secret_key()

    app.config.update(
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=Config.PERMANENT_SESSION_LIFETIME_SECONDS),
        SESSION_COOKIE_SECURE=Config.SESSION_COOKIE_SECURE,
        SESSION_COOKIE_HTTPONLY=Config.SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SAMESITE=Config.SESSION_COOKIE_SAMESITE,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=Config.WTF_CSRF_TIME_LIMIT,
        WTF_CSRF_SSL_STRICT=Config.WTF_CSRF_SSL_STRICT,
        WTF_CSRF_CHECK_DEFAULT=True,
        MAX_CONTENT_LENGTH=Config.MAX_CONTENT_LENGTH,
        TRAP_HTTP_EXCEPTIONS=False,
        TRAP_BAD_REQUEST_ERRORS=False,
        PROPAGATE_EXCEPTIONS=False,
    )

    # Расширения
    csrf.init_app(app)
    limiter.init_app(app)
    app.config['RATELIMIT_DEFAULT'] = Config.DEFAULT_LIMIT

    # Security-заголовки
    init_talisman(app)

    # Закрытие БД после запроса
    app.teardown_appcontext(close_db)

    # Регистрация blueprints
    from blueprints.auth import bp as auth_bp
    from blueprints.dashboard import bp as dashboard_bp
    from blueprints.clients import bp as clients_bp
    from blueprints.orders import bp as orders_bp
    from blueprints.materials import bp as materials_bp
    from blueprints.workers import bp as workers_bp
    from blueprints.payments import bp as payments_bp
    from blueprints.reports import bp as reports_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(workers_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Контекст для шаблонов
    from utils import current_user, has_role

    @app.context_processor
    def inject_user():
        return {
            'current_user': current_user(),
            'has_role': has_role,
            'ORDER_STATUSES': Config.ORDER_STATUSES,
            'WORK_TYPES': Config.WORK_TYPES,
        }

    # Обработчики ошибок
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        print(f'CSRF отклонён: {e.description}')
        from flask import flash, redirect, url_for
        flash('Ошибка безопасности: обновите страницу и попробуйте снова.', 'error')
        return redirect(url_for('auth.login'))

    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import request, render_template
        from flask_limiter.util import get_remote_address
        print(f'Rate limit: IP={get_remote_address()}')
        return render_template('login.html',
                               error429=True,
                               error_message=str(e.description)), 429

    @app.errorhandler(403)
    def err403(e):
        return render_template('error.html', code=403,
                               message='Недостаточно прав для доступа к странице'), 403

    @app.errorhandler(404)
    def err404(e):
        return render_template('error.html', code=404,
                               message='Страница не найдена'), 404

    @app.errorhandler(405)
    def err405(e):
        return render_template('error.html', code=405,
                               message='Метод не разрешён'), 405

    @app.errorhandler(500)
    def err500(e):
        tb = traceback.format_exc()
        print('=' * 60)
        print('ВНУТРЕННЯЯ ОШИБКА СЕРВЕРА')
        print(tb)
        print('=' * 60)
        return render_template('error.html', code=500,
                               message='Внутренняя ошибка сервера'), 500

    return app


def print_diagnostics():
    print('=' * 60)
    print('АИС «Ателье» — диагностика')
    print('=' * 60)
    print(f'Режим         : {"РАЗРАБОТКА" if Config.IS_DEV else "ПРОДАКШЕН"}')
    print(f'Secure cookie : {Config.SESSION_COOKIE_SECURE}')
    print(f'CSRF time     : {Config.WTF_CSRF_TIME_LIMIT} сек')
    print(f'STATIC_DIR    : {Config.STATIC_DIR} (есть: {os.path.isdir(Config.STATIC_DIR)})')
    print(f'TEMPLATES_DIR : {Config.TEMPLATES_DIR} (есть: {os.path.isdir(Config.TEMPLATES_DIR)})')
    print(f'DB_PATH       : {Config.DATABASE} (есть: {os.path.isfile(Config.DATABASE)})')
    print(f'SCHEMA        : {Config.STATIC_DIR}/../schema.sql')
    print(f'style.css     : {os.path.join(Config.STATIC_DIR, "css", "style.css")} '
          f'(есть: {os.path.isfile(os.path.join(Config.STATIC_DIR, "css", "style.css"))})')
    print(f'base.html     : {os.path.join(Config.TEMPLATES_DIR, "base.html")} '
          f'(есть: {os.path.isfile(os.path.join(Config.TEMPLATES_DIR, "base.html"))})')
    print('=' * 60)
    print('ЗАЩИТА:')
    print('  [+] CSRF (Flask-WTF)')
    print('  [+] Rate limiting (Flask-Limiter)')
    print('  [+] Security headers (Flask-Talisman)')
    print(f'  [+] Cookies: Secure={Config.SESSION_COOKIE_SECURE}, HttpOnly, SameSite=Lax')
    print('  [+] SECRET_KEY: 64 hex (.secret_key)')
    print('  [+] Валидация всех входных данных')
    print('  [+] Параметризованные SQL-запросы')
    print('=' * 60)


app = create_app()


if __name__ == '__main__':
    print_diagnostics()
    init_db()
    print('Открой: http://localhost:5000')
    print('Первый вход: admin / admin123')
    print('Сразу смени пароль через Администрирование!')
    print('=' * 60)
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)