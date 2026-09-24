import os
import sqlite3
from flask import g
from werkzeug.security import generate_password_hash
from config import Config


SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')


def get_db():
    """Соединение с БД на время запроса."""
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(exc=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def q(sql, params=(), one=False):
    """SELECT с параметризацией."""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    lid = cur.lastrowid
    cur.close()
    return lid


def init_db():
    """Создаёт таблицы и демо-данные."""
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema = f.read()

    db = sqlite3.connect(Config.DATABASE)
    db.executescript(schema)
    db.commit()

    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        demo = [
            ('admin', 'Администратор системы', 'admin123', 'admin'),
            ('reception', 'Приёмщик заказов', 'reception123', 'receptionist'),
            ('director', 'Директор ателье', 'director123', 'director'),
            ('worker', 'Портной Иванов И.И.', 'worker123', 'worker'),
        ]
        for u, fn, pw, r in demo:
            db.execute(
                'INSERT INTO users (username, full_name, password_hash, role) '
                'VALUES (?, ?, ?, ?)',
                (u, fn, generate_password_hash(pw), r))

    if db.execute('SELECT COUNT(*) FROM workers').fetchone()[0] == 0:
        db.execute("INSERT INTO workers (full_name, specialization, rate) "
                   "VALUES ('Иванов Иван Иванович', 'портной', 1500)")
        db.execute("INSERT INTO workers (full_name, specialization, rate) "
                   "VALUES ('Петрова Анна Сергеевна', 'закройщик', 1800)")

    if db.execute('SELECT COUNT(*) FROM materials').fetchone()[0] == 0:
        db.execute("INSERT INTO materials (name, kind, unit, stock, min_stock, price) "
                   "VALUES ('Ткань хлопок', 'ткань', 'м', 50, 10, 650)")
        db.execute("INSERT INTO materials (name, kind, unit, stock, min_stock, price) "
                   "VALUES ('Молния 20 см', 'фурнитура', 'шт', 100, 20, 45)")

    db.commit()
    db.close()