/* ============================================================
   АИС «Ателье» — клиентские скрипты
   ============================================================ */

function addRow() {
  const tbody = document.querySelector('#items-table tbody');
  if (!tbody) return;
  const tr = tbody.rows[0].cloneNode(true);
  tr.querySelectorAll('input').forEach(input => {
    if (input.type !== 'number') input.value = '';
    if (input.name === 'item_qty[]') input.value = '1';
    if (input.name === 'item_price[]') input.value = '0';
  });
  tbody.appendChild(tr);
  recalc();
}

function removeRow(btn) {
  const tbody = document.querySelector('#items-table tbody');
  if (!tbody) return;
  if (tbody.rows.length > 1) btn.closest('tr').remove();
  recalc();
}

function recalc() {
  const totalEl = document.getElementById('total');
  if (!totalEl) return;
  let total = 0;
  document.querySelectorAll('#items-table tbody tr').forEach(tr => {
    const qEl = tr.querySelector('input[name="item_qty[]"]');
    const pEl = tr.querySelector('input[name="item_price[]"]');
    if (!qEl || !pEl) return;
    total += (parseFloat(qEl.value) || 0) * (parseFloat(pEl.value) || 0);
  });
  totalEl.textContent = total.toFixed(2);
}

function setupConfirmation() {
  document.querySelectorAll('form').forEach(form => {
    const hasDanger = form.querySelector('button[type="submit"].btn-danger');
    const msg = form.dataset.confirm;
    if (hasDanger || msg) {
      form.addEventListener('submit', e => {
        if (!confirm(msg || 'Вы уверены? Действие необратимо.')) {
          e.preventDefault();
        }
      });
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('input', e => {
    if (e.target.closest('#items-table')) recalc();
  });
  recalc();
  setupConfirmation();
});

window.addRow = addRow;
window.removeRow = removeRow;