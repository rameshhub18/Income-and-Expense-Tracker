/* =============================================
   BUDGET PAGE — budget.js
   ============================================= */

// ── Theme ─────────────────────────────────────
const themeToggle = document.getElementById('themeToggle');
const themeIcon   = document.getElementById('themeIcon');
const savedTheme  = localStorage.getItem('theme') || 'light';
applyTheme(savedTheme);

themeToggle?.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  if (themeIcon) themeIcon.className = theme === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
}

// ── Sidebar toggle ────────────────────────────
const sidebar        = document.getElementById('sidebar');
const dashMain       = document.getElementById('dashMain');
const hamburger      = document.getElementById('hamburger');
const sidebarClose   = document.getElementById('sidebarClose');
const sidebarOverlay = document.getElementById('sidebarOverlay');

hamburger?.addEventListener('click', () => {
  if (window.innerWidth <= 768) {
    sidebar.classList.toggle('mobile-open');
    sidebarOverlay.classList.toggle('show');
  } else {
    sidebar.classList.toggle('collapsed');
    dashMain.classList.toggle('expanded');
  }
});

sidebarClose?.addEventListener('click', closeSidebar);
sidebarOverlay?.addEventListener('click', closeSidebar);

function closeSidebar() {
  sidebar.classList.remove('mobile-open');
  sidebarOverlay.classList.remove('show');
}

// ── Month selector → reload page ─────────────
document.getElementById('monthSelect')?.addEventListener('change', function () {
  window.location.href = `/budget?month=${this.value}`;
});

// ── Modal ─────────────────────────────────────
const modalOverlay  = document.getElementById('budgetModalOverlay');
const modalClose    = document.getElementById('budgetModalClose');
const budgetForm    = document.getElementById('budgetForm');
const modalTitle    = document.getElementById('budgetModalTitle');
const formAction    = document.getElementById('budgetFormAction');
const formId        = document.getElementById('budgetFormId');

// Multiple open triggers
document.getElementById('openAddModal')?.addEventListener('click',  () => openModal());
document.getElementById('openAddModal2')?.addEventListener('click', () => openModal());
modalClose?.addEventListener('click', closeModal);
modalOverlay?.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });

function openModal(data = null) {
  modalOverlay.classList.add('open');

  if (data) {
    modalTitle.textContent = 'Edit Budget Goal';
    formAction.value = 'edit';
    formId.value     = data.id;
    document.getElementById('budgetCategory').value = data.category;
    document.getElementById('budgetAmount').value   = data.amount;
    document.getElementById('budgetMonth').value    = data.month;
    document.getElementById('budgetSubmitBtn').innerHTML = 'Save Changes <i class="ri-check-line"></i>';
  } else {
    modalTitle.textContent = 'Set Budget Goal';
    formAction.value = 'add';
    formId.value     = '';
    // Reset only amount, keep category and month intact
    document.getElementById('budgetAmount').value   = '';
    document.getElementById('budgetCategory').value = '';
    document.getElementById('budgetMonth').value    = SELECTED_MONTH;
    document.getElementById('budgetSubmitBtn').innerHTML = 'Save Budget Goal <i class="ri-check-line"></i>';
  }

  // Focus amount field after short delay
  setTimeout(() => document.getElementById('budgetAmount')?.focus(), 100);
}

function closeModal() {
  modalOverlay.classList.remove('open');
}

// ── Form submit ───────────────────────────────
budgetForm?.addEventListener('submit', async (e) => {
  e.preventDefault();

  const category = document.getElementById('budgetCategory').value;
  const amount   = document.getElementById('budgetAmount').value;
  const month    = document.getElementById('budgetMonth').value;

  // Client-side validation
  if (!category) {
    alert('Please select a category.');
    document.getElementById('budgetCategory').focus();
    return;
  }
  if (!amount || parseFloat(amount) <= 0) {
    alert('Please enter a valid amount.');
    document.getElementById('budgetAmount').focus();
    return;
  }
  if (!month) {
    alert('Please select a month.');
    document.getElementById('budgetMonth').focus();
    return;
  }

  const btn = document.getElementById('budgetSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  const action = formAction.value;
  const url    = action === 'add' ? '/api/budget/add' : '/api/budget/edit';

  const fd = new FormData();
  if (action === 'edit') fd.append('id', formId.value);
  fd.append('category', category);
  fd.append('amount',   amount);
  fd.append('month',    month);

  try {
    const res  = await fetch(url, { method: 'POST', body: fd });
    const json = await res.json();
    console.log('API Response:', json); // Debug log
    if (json.success) {
      closeModal();
      location.reload();
    } else {
      alert(json.message || 'Something went wrong.');
    }
  } catch (err) {
    console.error('Network error:', err); // Debug log
    alert('Network error. Please try again.');
  } finally {
    btn.disabled = false;
  }
});

// ── Edit ──────────────────────────────────────
document.querySelectorAll('.edit-budget-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    openModal({
      id:       btn.dataset.id,
      category: btn.dataset.category,
      amount:   btn.dataset.amount,
      month:    btn.dataset.month,
    });
  });
});

// ── Delete ────────────────────────────────────
document.querySelectorAll('.delete-budget-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    if (!confirm('Delete this budget?')) return;
    const id   = btn.dataset.id;
    const card = btn.closest('.budget-card');

    const fd = new FormData();
    fd.append('id', id);

    const res  = await fetch('/api/budget/delete', { method: 'POST', body: fd });
    const json = await res.json();

    if (json.success) {
      card.classList.add('removing');
      setTimeout(() => card.remove(), 300);
    } else {
      alert(json.message || 'Could not delete.');
    }
  });
});

// ── Animate progress bars + rings on load ────
window.addEventListener('load', () => {
  // Progress bars
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const pct = parseFloat(bar.dataset.pct) || 0;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = Math.min(pct, 100) + '%'; }, 150);
  });

  // SVG rings — animate stroke-dasharray from 0 to target
  document.querySelectorAll('.budget-ring__fill').forEach(circle => {
    const full = parseFloat(circle.getAttribute('stroke-dasharray')?.split(' ')[0]) || 0;
    circle.setAttribute('stroke-dasharray', `0 213.6`);
    setTimeout(() => {
      circle.style.transition = 'stroke-dasharray .8s cubic-bezier(.4,0,.2,1)';
      circle.setAttribute('stroke-dasharray', `${full} 213.6`);
    }, 200);
  });
});
