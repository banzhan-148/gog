from flask import Blueprint, render_template

from db import q
from utils import login_required

bp = Blueprint('payments', __name__, url_prefix='/payments')


@bp.route('/')
@login_required
def index():
    items = q("""SELECT p.*, o.number AS order_number,
                        c.full_name AS client_name
                 FROM payments p
                 LEFT JOIN orders o ON o.id=p.order_id
                 LEFT JOIN clients c ON c.id=o.client_id
                 WHERE p.is_deleted=0
                 ORDER BY p.created_at DESC LIMIT 300""")
    total = q("SELECT COALESCE(SUM(amount),0) s FROM payments "
              "WHERE is_deleted=0", one=True)['s'] or 0
    return render_template('payments.html', payments=items, total=total)