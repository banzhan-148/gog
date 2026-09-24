import json
import traceback
from datetime import datetime, date

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort)

from db import q, execute
from utils import (login_required, role_required,
                   clean_text, clean_phone, clean_email,
                   log_action)

bp = Blueprint('clients', __name__, url_prefix='/clients')


@bp.route('/')
@login_required
def index():
    term = clean_text(request.args.get('q', ''), 100)
    if term:
        like = f'%{term}%'
        rows = q("""SELECT * FROM clients WHERE is_deleted=0
                    AND (full_name LIKE ? OR phone LIKE ?)
                    ORDER BY full_name LIMIT 200""", (like, like))
    else:
        rows = q("SELECT * FROM clients WHERE is_deleted=0 "
                 "ORDER BY full_name LIMIT 200")
    return render_template('clients.html', clients=rows, q=term)


@bp.route('/new', methods=['POST'])
@login_required
@role_required('admin', 'receptionist')
def new():
    try:
        full_name = clean_text(request.form.get('full_name'), 128)
        phone = clean_phone(request.form.get('phone'))
        email = clean_email(request.form.get('email'))
        birth = clean_text(request.form.get('birth_date'), 20)

        if not full_name:
            flash('ФИО обязательно', 'error')
            return redirect(url_for('clients.index'))

        dup = q("SELECT id FROM clients WHERE is_deleted=0 "
                "AND full_name=? AND IFNULL(phone,'')=?",
                (full_name, phone), one=True)
        if dup:
            flash(f'Клиент с такими данными уже есть (ID={dup["id"]})', 'warning')
            return redirect(url_for('clients.detail', cid=dup['id']))

        birth_date = None
        if birth:
            try:
                birth_date = datetime.strptime(birth, '%Y-%m-%d').date().isoformat()
            except ValueError:
                birth_date = None

        cid = execute(
            "INSERT INTO clients (full_name, phone, email, birth_date) "
            "VALUES (?, ?, ?, ?)",
            (full_name, phone, email, birth_date))
        log_action(f'Создан клиент: {full_name}', 'client', cid)
        flash('Клиент добавлен', 'success')
        return redirect(url_for('clients.detail', cid=cid))
    except Exception:
        traceback.print_exc()
        flash('Ошибка при создании клиента', 'error')
        return redirect(url_for('clients.index'))


@bp.route('/<int:cid>')
@login_required
def detail(cid):
    c = q("SELECT * FROM clients WHERE id=? AND is_deleted=0", (cid,), one=True)
    if not c:
        abort(404)
    orders = q("""SELECT o.*, w.full_name AS worker_name
                  FROM orders o LEFT JOIN workers w ON w.id=o.worker_id
                  WHERE o.client_id=? AND o.is_deleted=0
                  ORDER BY o.created_at DESC""", (cid,))
    measurements = q("SELECT * FROM measurements WHERE client_id=? "
                     "ORDER BY taken_at DESC", (cid,))
    for m in measurements:
        try:
            m['data'] = json.loads(m['data_json'])
        except Exception:
            m['data'] = {}
    return render_template('client_detail.html', client=c, orders=orders,
                           measurements=measurements)


@bp.route('/<int:cid>/measurements', methods=['POST'])
@login_required
@role_required('admin', 'receptionist')
def measurement_add(cid):
    raw = (request.form.get('data_json') or '').strip()
    if len(raw) > 5000:
        flash('Слишком большой JSON мерок', 'error')
        return redirect(url_for('clients.detail', cid=cid))
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError('Должен быть объект')
    except Exception:
        flash('Некорректный JSON (пример: {"рост":170,"обхват_груди":96})', 'error')
        return redirect(url_for('clients.detail', cid=cid))
    execute("INSERT INTO measurements (client_id, taken_at, data_json, note) "
            "VALUES (?, ?, ?, ?)",
            (cid, date.today().isoformat(),
             json.dumps(parsed, ensure_ascii=False),
             clean_text(request.form.get('note'), 255)))
    log_action('Добавлены мерки', 'client', cid)
    flash('Мерки сохранены', 'success')
    return redirect(url_for('clients.detail', cid=cid))