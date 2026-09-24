import io
import csv
from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, request, make_response

from db import q
from utils import login_required, role_required, clean_text

bp = Blueprint('reports', __name__, url_prefix='/reports')


def _get_range():
    d_from = clean_text(request.args.get('from'), 20) or \
             (date.today() - timedelta(days=30)).isoformat()
    d_to = clean_text(request.args.get('to'), 20) or date.today().isoformat()
    try:
        datetime.fromisoformat(d_from)
        datetime.fromisoformat(d_to)
    except ValueError:
        d_from = (date.today() - timedelta(days=30)).isoformat()
        d_to = date.today().isoformat()
    return d_from, d_to


@bp.route('/')
@login_required
@role_required('admin', 'director')
def index():
    d_from, d_to = _get_range()

    revenue = q("SELECT COALESCE(SUM(amount),0) s FROM payments "
                "WHERE is_deleted=0 AND date(created_at) BETWEEN ? AND ?",
                (d_from, d_to), one=True)['s'] or 0

    by_status = q("""SELECT status, COUNT(*) c FROM orders
                     WHERE is_deleted=0 AND date(created_at) BETWEEN ? AND ?
                     GROUP BY status""", (d_from, d_to))

    by_worker = q("""
        SELECT w.full_name AS name,
               (SELECT COUNT(*) FROM orders o WHERE o.worker_id=w.id
                AND o.is_deleted=0 AND date(o.created_at) BETWEEN ? AND ?) AS cnt,
               (SELECT COALESCE(SUM(total),0) FROM orders o WHERE o.worker_id=w.id
                AND o.is_deleted=0 AND date(o.created_at) BETWEEN ? AND ?) AS s
        FROM workers w
        ORDER BY w.full_name
    """, (d_from, d_to, d_from, d_to))

    low_materials = q("SELECT * FROM materials WHERE stock <= min_stock")

    return render_template('reports.html',
                           d_from=d_from, d_to=d_to,
                           revenue=revenue, by_status=by_status,
                           by_worker=by_worker, low_materials=low_materials)


@bp.route('/export.csv')
@login_required
@role_required('admin', 'director')
def export_csv():
    d_from, d_to = _get_range()
    rows = q("""SELECT o.*, c.full_name AS client_name, w.full_name AS worker_name
                FROM orders o
                LEFT JOIN clients c ON c.id=o.client_id
                LEFT JOIN workers w ON w.id=o.worker_id
                WHERE o.is_deleted=0 AND date(o.created_at) BETWEEN ? AND ?
                ORDER BY o.created_at""", (d_from, d_to))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(['Номер', 'Дата', 'Клиент', 'Исполнитель', 'Вид работ',
                'Статус', 'Сумма', 'Оплачено', 'Долг', 'Срок'])
    for o in rows:
        debt = round((o['total'] or 0) - (o['paid'] or 0), 2)
        w.writerow([o['number'],
                    (o['created_at'] or '')[:10],
                    o['client_name'] or '',
                    o['worker_name'] or '',
                    o['work_type'], o['status'],
                    f"{o['total']:.2f}", f"{o['paid']:.2f}", f"{debt:.2f}",
                    o['due_date'] or ''])
    data = '\ufeff' + buf.getvalue()
    resp = make_response(data)
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = \
        f'attachment; filename=report_{d_from}_{d_to}.csv'
    return resp