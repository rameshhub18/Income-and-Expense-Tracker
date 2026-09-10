/* =============================================
   NOTIFICATIONS PAGE — notifications.js
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

sidebarClose?.addEventListener('click', () => {
  sidebar.classList.remove('mobile-open');
  sidebarOverlay.classList.remove('show');
});

sidebarOverlay?.addEventListener('click', () => {
  sidebar.classList.remove('mobile-open');
  sidebarOverlay.classList.remove('show');
});

// ── Helpers ───────────────────────────────────
const unreadCountEl = document.getElementById('unreadCount');

function updateUnreadCount() {
  const unread = document.querySelectorAll('.notif-item--unread').length;
  if (unreadCountEl) {
    unreadCountEl.textContent = `${unread} unread`;
  }
}

function removeItem(el) {
  el.classList.add('removing');
  setTimeout(() => {
    el.remove();
    updateUnreadCount();
    checkEmpty();
  }, 300);
}

function checkEmpty() {
  const list = document.getElementById('notifList');
  if (list && list.querySelectorAll('.notif-item').length === 0) {
    list.innerHTML = `
      <div class="notif-empty" id="emptyState">
        <i class="ri-notification-off-line"></i>
        <p>You're all caught up! No notifications.</p>
      </div>`;
  }
}

async function post(url, data = {}) {
  const fd = new FormData();
  Object.entries(data).forEach(([k, v]) => fd.append(k, v));
  const res = await fetch(url, { method: 'POST', body: fd });
  return res.json();
}

// ── Mark single as read ───────────────────────
document.querySelectorAll('.read-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const id   = btn.dataset.id;
    const item = btn.closest('.notif-item');
    const res  = await post('/api/notifications/mark-read', { id });
    if (res.success) {
      item.classList.remove('notif-item--unread');
      btn.remove();
      updateUnreadCount();
    }
  });
});

// ── Dismiss single ────────────────────────────
document.querySelectorAll('.dismiss-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const id   = btn.dataset.id;
    const item = btn.closest('.notif-item');
    const res  = await post('/api/notifications/dismiss', { id });
    if (res.success) removeItem(item);
  });
});

// ── Mark all as read ──────────────────────────
document.getElementById('markAllRead')?.addEventListener('click', async () => {
  const res = await post('/api/notifications/mark-all-read');
  if (res.success) {
    document.querySelectorAll('.notif-item--unread').forEach(item => {
      item.classList.remove('notif-item--unread');
      item.querySelector('.read-btn')?.remove();
    });
    updateUnreadCount();
  }
});

// ── Clear all ─────────────────────────────────
document.getElementById('clearAllBtn')?.addEventListener('click', async () => {
  if (!confirm('Clear all notifications?')) return;
  const res = await post('/api/notifications/clear-all');
  if (res.success) {
    document.querySelectorAll('.notif-item').forEach(item => removeItem(item));
  }
});

// ── Filter tabs ───────────────────────────────
document.querySelectorAll('.notif-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.notif-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    const filter = tab.dataset.filter;
    const filterTypes = filter.split(',').map(t => t.trim()); // Support multiple types
    
    document.querySelectorAll('.notif-item').forEach(item => {
      const itemType = item.dataset.type;
      const matches = filter === 'all' || filterTypes.includes(itemType);
      item.style.display = matches ? '' : 'none';
    });
  });
});
