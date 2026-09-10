/* =============================================
   DASHBOARD — dashboard.js
   ============================================= */

// ── Mobile search toggle ──────────────────────
const mobileSearchBtn  = document.getElementById('mobileSearchBtn');
const mobileSearchBar  = document.getElementById('mobileSearchBar');
const mobileSearchClose= document.getElementById('mobileSearchClose');
const mobileSearchInput= document.getElementById('mobileSearchInput');

function checkMobileSearch() {
  if (window.innerWidth <= 768) {
    mobileSearchBtn && (mobileSearchBtn.style.display = 'flex');
  } else {
    mobileSearchBtn && (mobileSearchBtn.style.display = 'none');
    mobileSearchBar && mobileSearchBar.classList.remove('open');
  }
}

checkMobileSearch();
window.addEventListener('resize', checkMobileSearch);

mobileSearchBtn?.addEventListener('click', () => {
  mobileSearchBar.classList.add('open');
  mobileSearchInput?.focus();
});

mobileSearchClose?.addEventListener('click', () => {
  mobileSearchBar.classList.remove('open');
});

// Sync mobile search with table filter
mobileSearchInput?.addEventListener('input', function () {
  const query = this.value.toLowerCase().trim();
  const rows = document.querySelectorAll('#txBody tr');
  
  if (!query) {
    rows.forEach(row => row.style.display = '');
    return;
  }
  
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
});

// ── Theme ─────────────────────────────────────
const themeToggle = document.getElementById('themeToggle');
const themeIcon   = document.getElementById('themeIcon');

const savedTheme = localStorage.getItem('theme') || 'light';
applyTheme(savedTheme);

themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  themeIcon.className = theme === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
}

// ── Sidebar toggle ────────────────────────────
const sidebar        = document.getElementById('sidebar');
const dashMain       = document.getElementById('dashMain');
const hamburger      = document.getElementById('hamburger');
const sidebarClose   = document.getElementById('sidebarClose');
const sidebarOverlay = document.getElementById('sidebarOverlay');

hamburger.addEventListener('click', () => {
  if (window.innerWidth <= 768) {
    sidebar.classList.toggle('mobile-open');
    sidebarOverlay.classList.toggle('show');
  } else {
    sidebar.classList.toggle('collapsed');
    dashMain.classList.toggle('expanded');
  }
});

sidebarClose?.addEventListener('click', closeSidebar);
sidebarOverlay.addEventListener('click', closeSidebar);

function closeSidebar() {
  sidebar.classList.remove('mobile-open');
  sidebarOverlay.classList.remove('show');
}

// ── Sidebar quick-add links — auto-open modal from URL param ──
const addParam = new URLSearchParams(window.location.search).get('add');
if (addParam === 'income' || addParam === 'expense') {
  // Clean the URL without reloading
  window.history.replaceState({}, '', window.location.pathname);
  // Wait for DOM + JS to be ready then open modal
  window.addEventListener('load', () => openModal(addParam));
}

// ── Count-up animation ────────────────────────
document.querySelectorAll('.count-up').forEach(el => {
  const target = parseFloat(el.dataset.target) || 0;
  const isNeg  = target < 0;
  const abs    = Math.abs(target);
  let start    = 0;
  const dur    = 1200;
  const step   = 16;
  const inc    = abs / (dur / step);

  const timer = setInterval(() => {
    start += inc;
    if (start >= abs) { start = abs; clearInterval(timer); }
    el.textContent = (isNeg ? '-\u20B9' : '\u20B9') + start.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }, step);
});

// ── Charts ────────────────────────────────────
const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark';
const gridColor = () => isDark() ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.06)';
const textColor = () => isDark() ? '#94a3b8' : '#64748b';

// Bar chart — monthly income vs expense
const barCtx = document.getElementById('barChart')?.getContext('2d');
if (barCtx) {
  const labels  = MONTHLY_DATA.map(d => d.month);
  const incomes = MONTHLY_DATA.map(d => parseFloat(d.income));
  const expenses= MONTHLY_DATA.map(d => parseFloat(d.expense));

  // Fallback sample data if no real data
  const finalLabels   = labels.length   ? labels   : ['Jan','Feb','Mar','Apr','May','Jun'];
  const finalIncomes  = incomes.length  ? incomes  : [3200,4100,3800,5000,4600,6200];
  const finalExpenses = expenses.length ? expenses : [1800,2200,1900,2800,2100,1914];

  new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: finalLabels,
      datasets: [
        {
          label: 'Income',
          data: finalIncomes,
          backgroundColor: 'rgba(16,185,129,.75)',
          borderRadius: 6,
        },
        {
          label: 'Expense',
          data: finalExpenses,
          backgroundColor: 'rgba(239,68,68,.75)',
          borderRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: textColor() } } },
      scales: {
        x: { ticks: { color: textColor() }, grid: { color: gridColor() } },
        y: { ticks: { color: textColor() }, grid: { color: gridColor() } }
      }
    }
  });
}

// Pie chart — expense by category
const pieCtx = document.getElementById('pieChart')?.getContext('2d');
if (pieCtx) {
  const catLabels = CATEGORY_DATA.map(d => d.category);
  const catTotals = CATEGORY_DATA.map(d => parseFloat(d.total));

  const finalCatLabels = catLabels.length ? catLabels : ['Food','Transport','Shopping','Bills','Health','Other'];
  const finalCatTotals = catTotals.length ? catTotals : [420,180,350,290,120,200];

  new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: finalCatLabels,
      datasets: [{
        data: finalCatTotals,
        backgroundColor: ['#2563eb','#10b981','#f59e0b','#ef4444','#6366f1','#14b8a6'],
        borderWidth: 2,
        borderColor: isDark() ? '#1e293b' : '#fff',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: textColor(), padding: 12, font: { size: 12 } }
        }
      }
    }
  });
}

// ── Modal ─────────────────────────────────────
const modalOverlay = document.getElementById('modalOverlay');
const modalClose   = document.getElementById('modalClose');
const openModalBtn = document.getElementById('openModalBtn');
const fabBtn       = document.getElementById('fabBtn');
const txForm       = document.getElementById('txForm');
const modalTitle   = document.getElementById('modalTitle');
const formAction   = document.getElementById('formAction');
const formTxId     = document.getElementById('formTxId');

openModalBtn?.addEventListener('click', () => openModal());
fabBtn?.addEventListener('click', () => openModal());
modalClose?.addEventListener('click', closeModal);
modalOverlay?.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });

function openModal(type = 'income', data = null) {
  modalOverlay.classList.add('open');
  document.getElementById('txDate').valueAsDate = new Date();

  if (data) {
    // Edit mode
    modalTitle.textContent = 'Edit Transaction';
    formAction.value = 'edit';
    formTxId.value   = data.id;
    document.getElementById('txAmount').value   = data.amount;
    document.getElementById('txType').value     = data.type;
    document.getElementById('txCategory').value = data.category;
    document.getElementById('txDate').value     = data.date;
    document.getElementById('txDesc').value     = data.description || '';
    document.getElementById('txSubmitBtn').innerHTML = 'Save Changes <i class="ri-check-line"></i>';
  } else {
    // Add mode
    modalTitle.textContent = 'Add Transaction';
    formAction.value = 'add';
    formTxId.value   = '';
    txForm.reset();
    document.getElementById('txType').value = type;
    document.getElementById('txDate').valueAsDate = new Date();
    document.getElementById('txSubmitBtn').innerHTML = 'Add Transaction <i class="ri-check-line"></i>';
  }
}

function closeModal() {
  modalOverlay.classList.remove('open');
}

// ── Form submit (AJAX) ────────────────────────
txForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('txSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  const formData = new FormData(txForm);

  try {
    const res  = await fetch(API_URL, { method: 'POST', body: formData });
    const json = await res.json();

    if (json.success) {
      closeModal();
      location.reload(); // reload to reflect new data
    } else {
      alert(json.message || 'Something went wrong.');
    }
  } catch {
    alert('Network error. Please try again.');
  } finally {
    btn.disabled = false;
  }
});

// ── Delete transaction ────────────────────────
document.querySelectorAll('.delete-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    if (!confirm('Delete this transaction?')) return;
    const id = btn.dataset.id;

    const fd = new FormData();
    fd.append('action', 'delete');
    fd.append('tx_id', id);

    const res  = await fetch(API_URL, { method: 'POST', body: fd });
    const json = await res.json();

    if (json.success) {
      btn.closest('tr').remove();
    } else {
      alert(json.message || 'Could not delete.');
    }
  });
});

// ── Edit transaction ──────────────────────────
document.querySelectorAll('.edit-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const row = btn.closest('tr');
    openModal('income', {
      id:          btn.dataset.id,
      amount:      row.querySelector('.tx-amount').textContent.replace(/[^0-9.]/g, ''),
      type:        row.dataset.type,
      category:    row.dataset.category,
      date:        '',
      description: row.cells[3].textContent === '—' ? '' : row.cells[3].textContent,
    });
  });
});

// ── Search ────────────────────────────────────
document.getElementById('searchInput')?.addEventListener('input', function () {
  const query = this.value.toLowerCase().trim();
  const rows = document.querySelectorAll('#txBody tr');
  
  if (!query) {
    rows.forEach(row => row.style.display = '');
    return;
  }
  
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    const matches = text.includes(query);
    row.style.display = matches ? '' : 'none';
  });
});

// ── Filter ────────────────────────────────────
document.getElementById('applyFilter')?.addEventListener('click', () => {
  const from     = document.getElementById('filterFrom').value;
  const to       = document.getElementById('filterTo').value;
  const type     = document.getElementById('filterType').value.toLowerCase();
  const category = document.getElementById('filterCategory').value.toLowerCase();

  document.querySelectorAll('#txBody tr').forEach(row => {
    const rowType = row.dataset.type?.toLowerCase() || '';
    const rowCat  = row.dataset.category?.toLowerCase() || '';
    const dateCell= row.cells[0]?.textContent;
    const rowDate = dateCell ? new Date(dateCell) : null;

    let show = true;
    if (type     && rowType !== type)         show = false;
    if (category && rowCat !== category)      show = false;
    if (from     && rowDate && rowDate < new Date(from)) show = false;
    if (to       && rowDate && rowDate > new Date(to))   show = false;

    row.style.display = show ? '' : 'none';
  });
});

document.getElementById('clearFilter')?.addEventListener('click', () => {
  document.getElementById('filterFrom').value     = '';
  document.getElementById('filterTo').value       = '';
  document.getElementById('filterType').value     = '';
  document.getElementById('filterCategory').value = '';
  document.querySelectorAll('#txBody tr').forEach(r => r.style.display = '');
});

// ── Export CSV ────────────────────────────────
document.getElementById('exportCSV')?.addEventListener('click', () => {
  const rows   = document.querySelectorAll('#txBody tr:not([style*="none"])');
  const header = ['Date','Type','Category','Description','Amount'];
  const lines  = [header.join(',')];

  rows.forEach(row => {
    const cells = Array.from(row.querySelectorAll('td')).slice(0, 5);
    const vals  = cells.map(td => `"${td.textContent.trim()}"`);
    if (vals.length) lines.push(vals.join(','));
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'transactions.csv';
  a.click();
  URL.revokeObjectURL(url);
});

