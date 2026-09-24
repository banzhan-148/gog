from flask import Blueprint, render_template, request, redirect, url_for, flash

from db import q, execute
from utils import login_required, role_required, clean_text, safe_float, log_action

bp = Blueprint('workers', __name__, url_prefix='/workers')


@bp.route('/')
@login_required
def index():
    items = q("SELECT * FROM workers ORDER BY full_name")
    for w in items:
        cnt = q("SELECT COUNT(*) c FROM orders WHERE worker_id=? "
                "AND is_deleted=0 AND status NOT IN ('выдан','отменён')",
                (w['id'],), one=True)['c']
        w['load'] = cnt
    return render_template('workers.html', workers=items)


@bp.route('/new', methods=['POST'])
@login_required
@role_required('admin')
def new():
    full_name = clean_text(request.form.get('full_name'), 128)
    if not full_name:
        flash('ФИО обязательно', 'error')
        return redirect(url_for('workers.index'))
    wid = execute("INSERT INTO workers (full_name, specialization, rate) "
                  "VALUES (?, ?, ?)",
                  (full_name,
                   clean_text(request.form.get('specialization', ''), 64),
                   safe_float(request.form.get('rate'), 0, min_val=0,
                              max_val=10_000_000)))
    log_action('Создан исполнитель', 'worker', wid)
    flash('Исполнитель добавлен', 'success')
    return redirect(url_for('workers.index'))