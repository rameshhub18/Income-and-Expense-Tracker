/* =============================================
   REPORTS PAGE — reports.js
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

// ── Period selector ───────────────────────────
const periodSelect  = document.getElementById('periodSelect');
const customRange   = document.getElementById('customRange');

periodSelect?.addEventListener('change', () => {
  if (periodSelect.value === 'custom') {
    customRange.style.display = 'flex';
  } else {
    window.location.href = `/reports?period=${periodSelect.value}`;
  }
});

document.getElementById('applyCustom')?.addEventListener('click', () => {
  const from = document.getElementById('customFrom').value;
  const to   = document.getElementById('customTo').value;
  if (from && to) {
    window.location.href = `/reports?period=custom&from=${from}&to=${to}`;
  }
});

// ── Chart helpers ─────────────────────────────
const isDark    = () => document.documentElement.getAttribute('data-theme') === 'dark';
const gridColor = () => isDark() ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.06)';
const textColor = () => isDark() ? '#94a3b8' : '#64748b';

const PALETTE = ['#2563eb','#10b981','#f59e0b','#ef4444','#6366f1',
                 '#14b8a6','#f97316','#8b5cf6','#ec4899','#06b6d4'];

// ── 1. Trend line chart (daily income vs expense) ──
const trendCtx = document.getElementById('trendChart')?.getContext('2d');
if (trendCtx) {
  // Build date-keyed maps
  const incomeMap  = {};
  const expenseMap = {};

  DAILY_ROWS.forEach(r => {
    const d = r.date ? r.date.substring(0, 10) : '';
    if (r.type === 'income')  incomeMap[d]  = (incomeMap[d]  || 0) + parseFloat(r.total);
    if (r.type === 'expense') expenseMap[d] = (expenseMap[d] || 0) + parseFloat(r.total);
  });

  const allDates = [...new Set([...Object.keys(incomeMap), ...Object.keys(expenseMap)])].sort();

  // Fallback sample data
  const labels   = allDates.length ? allDates : ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const incomes  = allDates.length ? allDates.map(d => incomeMap[d]  || 0) : [200,0,350,0,500,0,150];
  const expenses = allDates.length ? allDates.map(d => expenseMap[d] || 0) : [80,120,60,200,90,150,40];

  new Chart(trendCtx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Income',
          data: incomes,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,.1)',
          fill: true,
          tension: .4,
          pointRadius: 3,
        },
        {
          label: 'Expense',
          data: expenses,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,.1)',
          fill: true,
          tension: .4,
          pointRadius: 3,
        }
      ]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: textColor() } } },
      scales: {
        x: { ticks: { color: textColor(), maxTicksLimit: 10 }, grid: { color: gridColor() } },
        y: { ticks: { color: textColor() }, grid: { color: gridColor() } }
      }
    }
  });
}

// ── 2. Expense doughnut ───────────────────────
const expPieCtx = document.getElementById('expensePieChart')?.getContext('2d');
if (expPieCtx) {
  const labels = EXPENSE_BY_CAT.length ? EXPENSE_BY_CAT.map(d => d.category) : ['Food','Transport','Bills','Shopping','Other'];
  const data   = EXPENSE_BY_CAT.length ? EXPENSE_BY_CAT.map(d => d.total)    : [420,180,290,350,200];

  new Chart(expPieCtx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: PALETTE,
        borderWidth: 2,
        borderColor: isDark() ? '#1e293b' : '#fff',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { color: textColor(), padding: 10, font: { size: 11 } } }
      }
    }
  });
}

// ── 3. Monthly bar chart ──────────────────────
const monthlyCtx = document.getElementById('monthlyBarChart')?.getContext('2d');
if (monthlyCtx) {
  const labels   = MONTHLY_DATA.length ? MONTHLY_DATA.map(d => d.month)   : ['Jan','Feb','Mar','Apr','May','Jun'];
  const incomes  = MONTHLY_DATA.length ? MONTHLY_DATA.map(d => d.income)  : [3200,4100,3800,5000,4600,6200];
  const expenses = MONTHLY_DATA.length ? MONTHLY_DATA.map(d => d.expense) : [1800,2200,1900,2800,2100,1914];

  new Chart(monthlyCtx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Income',  data: incomes,  backgroundColor: 'rgba(16,185,129,.75)', borderRadius: 5 },
        { label: 'Expense', data: expenses, backgroundColor: 'rgba(239,68,68,.75)',  borderRadius: 5 }
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

// ── 4. Income sources doughnut ────────────────
const incPieCtx = document.getElementById('incomePieChart')?.getContext('2d');
if (incPieCtx) {
  const labels = INCOME_BY_CAT.length ? INCOME_BY_CAT.map(d => d.category) : ['Salary','Freelance','Other'];
  const data   = INCOME_BY_CAT.length ? INCOME_BY_CAT.map(d => d.total)    : [3500,800,200];

  new Chart(incPieCtx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: ['#10b981','#2563eb','#6366f1','#f59e0b','#14b8a6'],
        borderWidth: 2,
        borderColor: isDark() ? '#1e293b' : '#fff',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { color: textColor(), padding: 10, font: { size: 11 } } }
      }
    }
  });
}
