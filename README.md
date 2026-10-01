АИС «Ателье»
Автоматизированная информационная система учёта заказов, клиентов, материалов и оплат для ателье пошива и ремонта одежды.

Стек: Python 3.12+ · Flask 3.1 · SQLite · Flask-WTF · Flask-Limiter · Flask-Talisman

Возможности
Модуль	Функции
Заказы	CRUD, статусы, позиции, списания материалов, оплаты, флаг долга, пагинация
Клиенты	CRUD, поиск, мерки (JSON), история заказов, пагинация
Материалы	CRUD, остатки, мин. остаток, списания по заказам
Исполнители	CRUD, нагрузка, активация/деактивация
Оплаты	журнал, привязка к заказам, транзакционное обновление paid
Отчёты	выручка, статусы, по исполнителям, низкие остатки, CSV-экспорт (защита от formula injection)
Админ	пользователи, роли, сброс паролей (политика ≥12 символов в prod), бэкап БД, аудит-лог
Безопасность	CSRF, rate-limit, CSP без unsafe-inline, роли, параметризованный SQL, транзакции
Быстрый старт (разработка)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # для тестов

# опционально: скопировать .env.example → .env
python run.py
# → http://localhost:5000
# DEV-логины: admin/admin123, reception/reception123, worker/worker123, director/director123
App factory
from run import create_app
app = create_app('development')   # development | testing | production
Тесты
pip install -r requirements-dev.txt
pytest
# или с покрытием:
pytest --cov=. --cov-report=term-missing
Покрыто: авторизация и роли, валидаторы, CSV-injection, создание заказа, атомарные оплаты и списания, политика паролей, API клиентов, пагинация.

Продакшен
См. DEPLOY.md и SECURITY.md.

Кратко:

FLASK_ENV=production
FLASK_SECRET_KEY — длинная случайная строка
ADMIN_PASSWORD ≥ 12 символов (создаётся только при первом запуске)
RATELIMIT_STORAGE_URI=redis://... (обязательно при нескольких воркерах)
HTTPS-прокси (nginx/caddy), Gunicorn/uWSGI
Регулярные бэкапы через /admin или cron + копия atelier.db
Структура проекта
atelier/
├── run.py              # create_app() + entry point
├── config.py           # Development / Testing / Production
├── db.py               # SQLite helpers + transactions
├── extensions.py       # CSRF, Limiter
├── security.py         # SECRET_KEY, Talisman/CSP
├── logging_config.py   # единый logging вместо print
├── utils.py            # auth, sanitizers, pagination
├── services/           # бизнес-логика (orders, payments, materials, clients, users)
├── blueprints/         # HTTP-слой
├── templates/          # Jinja2
├── static/             # css, js (CSP: только external)
├── tests/              # pytest
├── schema.sql
├── requirements.txt / .lock
├── SECURITY.md
└── DEPLOY.md
Роли
Роль	Доступ
admin	всё + пользователи, бэкап
receptionist	заказы, клиенты, оплаты, материалы (остатки)
worker	заказы (статусы, списания), материалы (просмотр)
director	дашборд, клиенты, оплаты, отчёты, флаг долга
Лицензия
