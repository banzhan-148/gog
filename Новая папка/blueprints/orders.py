import traceback
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort)

from config import Config
from db import q, execute
from utils import (login_required, role_required, has_role,
                   clean_text, safe_float, safe_int, log_action,
                   current_user)

bp = Blueprint('orders', __name__, url_prefix='/orders')


def _order_with_extra(o):
    o['debt'] = round((o['total'] or 0) - (o['paid'] or 0), 2)
    return o


@bp.route('/')
@login_required
def index():
    status = clean_text(request.args.get('status', ''), 32)
    term = clean_text(request.args.get('q', ''), 100)
    sql = """SELECT o.*, c.full_name AS client_name, w.full_name AS worker_name
             FROM orders o
             LEFT JOIN clients c ON c.id = o.client_id
             LEFT JOIN workers w ON w.id = o.worker_id
             WHERE o.is_deleted = 0"""
    params = []
    if status:
        sql += " AND o.status = ?"
        params.append(status)
    if term:
        sql += " AND (o.number LIKE ? OR c.full_name LIKE ? OR c.phone LIKE ?)"
        like = f'%{term}%'
        params += [like, like, like]
    sql += " ORDER BY o.created_at DESC LIMIT 300"
    rows = q(sql, params)
    for o in rows:
        _order_with_extra(o)
    return render_template('orders.html', orders=rows,
                           cur_status=status, q=term)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def new():
    if request.method == 'POST':
        try:
            client_id = safe_int(request.form.get('client_id'), 0, min_val=1)
            if not client_id or not q("SELECT id FROM clients WHERE id=? "
                                      "AND is_deleted=0", (client_id,), one=True):
                flash('Клиент не найден', 'error')
                return redirect(url_for('orders.new'))

            worker_id = request.form.get('worker_id') or None
            if worker_id:
                worker_id = safe_int(worker_id, 0, min_val=1) or None
                if worker_id and not q("SELECT id FROM workers WHERE id=? "
                                       "AND is_active=1", (worker_id,), one=True):
                    worker_id = None

            work_type = clean_text(request.form['work_type'], 32)
            if work_type not in Config.WORK_TYPES:
                work_type = 'пошив'
            description = clean_text(request.form.get('description'), 1000)
            due_date_raw = clean_text(request.form.get('due_date'), 20)

            names = request.form.getlist('item_name[]')
            qtys = request.form.getlist('item_qty[]')
            prices = request.form.getlist('item_price[]')
            items = []
            total = 0.0
            for n, qq, p in zip(names, qtys, prices):
                name = clean_text(n, 128)
                if not name:
                    continue
                qq = safe_int(qq, 1, min_val=1, max_val=10000)
                p = safe_float(p, 0, min_val=0, max_val=10_000_000)
                total += qq * p
                items.append((name, qq, p))

            last = q("SELECT id FROM orders ORDER BY id DESC LIMIT 1", one=True)
            seq = (last['id'] if last else 0) + 1
            number = f'AT-{datetime.utcnow().year}-{seq:05d}'

            due_date = None
            if due_date_raw:
                try:
                    due_date = datetime.strptime(due_date_raw, '%Y-%m-%d').date().isoformat()
                except ValueError:
                    due_date = None

            oid = execute("""INSERT INTO orders
                (number, client_id, worker_id, work_type, description,
                 status, total, paid, due_date, created_by)
                VALUES (?, ?, ?, ?, ?, 'принят', ?, 0, ?, ?)""",
                (number, client_id, worker_id,
                 work_type, description, total, due_date,
                 current_user()['id']))
            for name, qq, p in items:
                execute("INSERT INTO order_items (order_id, name, qty, price) "
                        "VALUES (?, ?, ?, ?)", (oid, name, qq, p))
            log_action(f'Создан заказ {number}', 'order', oid)
            flash(f'Заказ {number} создан', 'success')
            return redirect(url_for('orders.detail', oid=oid))
        except Exception:
            traceback.print_exc()
            flash('Ошибка создания заказа', 'error')
            return redirect(url_for('orders.new'))

    clients_list = q("SELECT * FROM clients WHERE is_deleted=0 ORDER BY full_name")
    workers_list = q("SELECT * FROM workers WHERE is_active=1 ORDER BY full_name")
    materials_list = q("SELECT * FROM materials ORDER BY name")
    return render_template('order_new.html', clients=clients_list,
                           workers=workers_list, materials=materials_list,
                           selected_client=request.args.get('client_id', ''))


@bp.route('/<int:oid>')
@login_required
def detail(oid):
    o = q("""SELECT o.*, c.full_name AS client_name, c.phone AS client_phone,
                    w.full_name AS worker_name
             FROM orders o
             LEFT JOIN clients c ON c.id=o.client_id
             LEFT JOIN workers w ON w.id=o.worker_id
             WHERE o.id=? AND o.is_deleted=0""", (oid,), one=True)
    if not o:
        abort(404)
    _order_with_extra(o)
    o['items'] = q("SELECT * FROM order_items WHERE order_id=?", (oid,))
    o['payments'] = q("SELECT * FROM payments WHERE order_id=? "
                      "ORDER BY created_at DESC", (oid,))
    o['writeoffs'] = q("""SELECT mw.*, m.name AS material_name, m.unit AS unit
                          FROM material_writeoffs mw
                          LEFT JOIN materials m ON m.id=mw.material_id
                          WHERE mw.order_id=? ORDER BY mw.created_at DESC""", (oid,))
    materials_list = q("SELECT * FROM materials ORDER BY name")
    return render_template('order_detail.html', order=o,
                           materials=materials_list)


@bp.route('/<int:oid>/status', methods=['POST'])
@login_required
def status(oid):
    o = q("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    if not o:
        abort(404)
    new_status = clean_text(request.form['status'], 32)
    if new_status not in Config.ORDER_STATUSES:
        flash('Некорректный статус', 'error')
        return redirect(url_for('orders.detail', oid=oid))
    debt = (o['total'] or 0) - (o['paid'] or 0)
    if new_status == 'выдан' and debt > 0 and not o['is_debt']:
        if not has_role('admin', 'director'):
            flash('Нельзя выдать заказ без полной оплаты', 'error')
            return redirect(url_for('orders.detail', oid=oid))
    execute("UPDATE orders SET status=? WHERE id=?", (new_status, oid))
    log_action(f'Статус заказа {o["number"]}: {o["status"]} -> {new_status}',
               'order', oid)
    flash('Статус обновлён', 'success')
    return redirect(url_for('orders.detail', oid=oid))


@bp.route('/<int:oid>/payment', methods=['POST'])
@login_required
@role_required('admin', 'receptionist')
def payment(oid):
    o = q("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    if not o:
        abort(404)
    amount = safe_float(request.form.get('amount'), 0, min_val=0.01,
                        max_val=10_000_000)
    if amount <= 0:
        flash('Сумма должна быть от 0.01 до 10 000 000', 'error')
        return redirect(url_for('orders.detail', oid=oid))
    method = clean_text(request.form.get('method', 'наличные'), 32)
    kind = clean_text(request.form.get('kind', 'доплата'), 32)
    execute("INSERT INTO payments (order_id, amount, method, kind) "
            "VALUES (?, ?, ?, ?)", (oid, amount, method, kind))
    new_paid = round((o['paid'] or 0) + amount, 2)
    execute("UPDATE orders SET paid=? WHERE id=?", (new_paid, oid))
    log_action(f'Оплата по заказу {o["number"]}: {amount} руб.', 'order', oid)
    flash('Платёж добавлен', 'success')
    return redirect(url_for('orders.detail', oid=oid))


@bp.route('/<int:oid>/writeoff', methods=['POST'])
@login_required
@role_required('admin', 'receptionist', 'worker')
def writeoff(oid):
    o = q("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    if not o:
        abort(404)
    mid = safe_int(request.form.get('material_id'), 0, min_val=1)
    qty = safe_float(request.form.get('qty'), 0, min_val=0.001, max_val=1_000_000)
    if not mid or qty <= 0:
        flash('Некорректные данные списания', 'error')
        return redirect(url_for('orders.detail', oid=oid))
    m = q("SELECT * FROM materials WHERE id=?", (mid,), one=True)
    if not m or qty > m['stock']:
        flash('Некорректное списание (недостаточно остатка)', 'error')
        return redirect(url_for('orders.detail', oid=oid))
    execute("INSERT INTO material_writeoffs (order_id, material_id, qty) "
            "VALUES (?, ?, ?)", (oid, mid, qty))
    execute("UPDATE materials SET stock=? WHERE id=?",
            (round(m['stock'] - qty, 3), mid))
    log_action(f'Списание материала {m["name"]}: {qty} {m["unit"]} '
               f'по заказу {o["number"]}', 'order', oid)
    flash('Материал списан', 'success')
    return redirect(url_for('orders.detail', oid=oid))


@bp.route('/<int:oid>/debt', methods=['POST'])
@login_required
@role_required('admin', 'director')
def debt(oid):
    o = q("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    if not o:
        abort(404)
    execute("UPDATE orders SET is_debt=1 WHERE id=?", (oid,))
    log_action(f'Разрешён отпуск в долг по заказу {o["number"]}', 'order', oid)
    flash('Отпуск в долг разрешён', 'warning')
    return redirect(url_for('orders.detail', oid=oid))


@bp.route('/<int:oid>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(oid):
    o = q("SELECT * FROM orders WHERE id=?", (oid,), one=True)
    if o:
        execute("UPDATE orders SET is_deleted=1 WHERE id=?", (oid,))
        log_action(f'Удалён заказ {o["number"]}', 'order', oid)
        flash('Заказ помечен как удалённый', 'warning')
    return redirect(url_for('orders.index'))