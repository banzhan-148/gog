from datetime import date
from flask import Blueprint, render_template

from db import q
from utils import login_required

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    today = date.today().isoformat()
    month_prefix = today[:7]
    stats = {
        'orders_active': q("SELECT COUNT(*) c FROM orders WHERE is_deleted=0 "
                           "AND status NOT IN ('выдан','отменён')", one=True)['c'],
        'orders_ready': q("SELECT COUNT(*) c FROM orders WHERE status='готов' "
                          "AND is_deleted=0", one=True)['c'],
        'orders_today': q("SELECT COUNT(*) c FROM orders WHERE is_deleted=0 "
                          "AND date(created_at)=?", (today,), one=True)['c'],
        'revenue_month': q("SELECT COALESCE(SUM(amount),0) s FROM payments "
                           "WHERE is_deleted=0 AND substr(created_at,1,7)=?",
                           (month_prefix,), one=True)['s'] or 0,
        'overdue': q("SELECT COUNT(*) c FROM orders WHERE is_deleted=0 "
                     "AND due_date < ? AND status NOT IN ('выдан','отменён') "
                     "AND due_date IS NOT NULL",
                     (today,), one=True)['c'],
        'materials_low': q("SELECT COUNT(*) c FROM materials "
                           "WHERE stock <= min_stock", one=True)['c'],
    }
    recent_orders = q("""
        SELECT o.*, c.full_name AS client_name
        FROM orders o
        LEFT JOIN clients c ON c.id = o.client_id
        WHERE o.is_deleted=0
        ORDER BY o.created_at DESC LIMIT 10
    """)
    return render_template('dashboard.html', stats=stats, recent_orders=recent_orders)