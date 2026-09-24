from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from db import q, execute
from utils import login_required, role_required, clean_text, safe_float, log_action

bp = Blueprint('materials', __name__, url_prefix='/materials')


@bp.route('/')
@login_required
def index():
    items = q("SELECT * FROM materials ORDER BY name")
    return render_template('materials.html', materials=items)


@bp.route('/new', methods=['POST'])
@login_required
@role_required('admin')
def new():
    name = clean_text(request.form.get('name'), 128)
    if not name:
        flash('Название материала обязательно', 'error')
        return redirect(url_for('materials.index'))
    mid = execute(
        "INSERT INTO materials (name, kind, unit, stock, min_stock, price) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name,
         clean_text(request.form.get('kind', ''), 64),
         clean_text(request.form.get('unit', 'м'), 16),
         safe_float(request.form.get('stock'), 0, min_val=0, max_val=1_000_000),
         safe_float(request.form.get('min_stock'), 0, min_val=0, max_val=1_000_000),
         safe_float(request.form.get('price'), 0, min_val=0, max_val=100_000_000)))
    log_action('Создан материал', 'material', mid)
    flash('Материал добавлен', 'success')
    return redirect(url_for('materials.index'))


@bp.route('/<int:mid>/stock', methods=['POST'])
@login_required
@role_required('admin', 'receptionist')
def stock(mid):
    m = q("SELECT * FROM materials WHERE id=?", (mid,), one=True)
    if not m:
        abort(404)
    delta = safe_float(request.form.get('delta'), 0, min_val=-1_000_000,
                       max_val=1_000_000)
    if delta == 0:
        flash('Введите ненулевое значение', 'error')
        return redirect(url_for('materials.index'))
    if m['stock'] + delta < 0:
        flash('Остаток не может быть отрицательным', 'error')
        return redirect(url_for('materials.index'))
    execute("UPDATE materials SET stock=? WHERE id=?",
            (round(m['stock'] + delta, 3), mid))
    log_action(f'Поступление/корректировка {m["name"]}: {delta}', 'material', mid)
    flash('Остаток обновлён', 'success')
    return redirect(url_for('materials.index'))