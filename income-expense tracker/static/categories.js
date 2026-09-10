/* =============================================
   CATEGORIES PAGE — categories.js
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

// ── Modal ─────────────────────────────────────
const modalOverlay = document.getElementById('catModalOverlay');
const modalClose   = document.getElementById('catModalClose');
const openAddBtn   = document.getElementById('openAddModal');
const catForm      = document.getElementById('catForm');
const modalTitle   = document.getElementById('catModalTitle');
const formAction   = document.getElementById('catFormAction');
const formId       = document.getElementById('catFormId');

openAddBtn?.addEventListener('click', () => openModal());
modalClose?.addEventListener('click', closeModal);
modalOverlay?.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });

function openModal(data = null) {
  modalOverlay.classList.add('open');

  if (data) {
    // Edit mode
    modalTitle.textContent = 'Edit Category';
    formAction.value = 'edit';
    formId.value     = data.id;
    document.getElementById('catName').value = data.name;
    document.getElementById('catType').value = data.type;
    selectColor(data.color);
    selectIcon(data.icon);
    document.getElementById('catSubmitBtn').innerHTML = 'Save Changes <i class="ri-check-line"></i>';
  } else {
    // Add mode
    modalTitle.textContent = 'Add Category';
    formAction.value = 'add';
    formId.value     = '';
    catForm.reset();
    selectColor('#2563eb');
    selectIcon('ri-price-tag-3-line');
    document.getElementById('catSubmitBtn').innerHTML = 'Add Category <i class="ri-check-line"></i>';
  }
  updatePreview();
}

function closeModal() {
  modalOverlay.classList.remove('open');
}

// ── Color picker ──────────────────────────────
let selectedColor = '#2563eb';

document.querySelectorAll('.color-swatch').forEach(btn => {
  btn.addEventListener('click', () => selectColor(btn.dataset.color));
});

document.getElementById('customColor')?.addEventListener('input', (e) => {
  selectColor(e.target.value);
});

function selectColor(color) {
  selectedColor = color;
  document.getElementById('catColor').value = color;
  document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('selected'));
  const match = document.querySelector(`.color-swatch[data-color="${color}"]`);
  if (match) match.classList.add('selected');
  updatePreview();
}

// ── Icon picker ───────────────────────────────
let selectedIcon = 'ri-price-tag-3-line';

document.querySelectorAll('.icon-swatch').forEach(btn => {
  btn.addEventListener('click', () => selectIcon(btn.dataset.icon));
});

function selectIcon(icon) {
  selectedIcon = icon;
  document.getElementById('catIcon').value = icon;
  document.querySelectorAll('.icon-swatch').forEach(s => s.classList.remove('selected'));
  const match = document.querySelector(`.icon-swatch[data-icon="${icon}"]`);
  if (match) match.classList.add('selected');
  updatePreview();
}

// ── Live preview ──────────────────────────────
function updatePreview() {
  const previewIcon = document.getElementById('previewIcon');
  const previewIconEl = document.getElementById('previewIconEl');
  const previewName = document.getElementById('previewName');

  previewIcon.style.background = selectedColor + '22';
  previewIcon.style.color = selectedColor;
  previewIconEl.className = selectedIcon;
  previewName.textContent = document.getElementById('catName').value || 'Category Name';
}

document.getElementById('catName')?.addEventListener('input', updatePreview);

// ── Form submit ───────────────────────────────
catForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('catSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  const action = formAction.value;
  const url    = action === 'add' ? '/api/categories/add' : '/api/categories/edit';

  const fd = new FormData();
  if (action === 'edit') fd.append('id', formId.value);
  fd.append('name',  document.getElementById('catName').value);
  fd.append('type',  document.getElementById('catType').value);
  fd.append('icon',  selectedIcon);
  fd.append('color', selectedColor);

  try {
    const res  = await fetch(url, { method: 'POST', body: fd });
    const json = await res.json();
    if (json.success) {
      closeModal();
      location.reload();
    } else {
      alert(json.message || 'Something went wrong.');
    }
  } catch {
    alert('Network error. Please try again.');
  } finally {
    btn.disabled = false;
  }
});

// ── Edit ──────────────────────────────────────
document.querySelectorAll('.edit-cat-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    openModal({
      id:    btn.dataset.id,
      name:  btn.dataset.name,
      type:  btn.dataset.type,
      icon:  btn.dataset.icon,
      color: btn.dataset.color,
    });
  });
});

// ── Delete ────────────────────────────────────
document.querySelectorAll('.delete-cat-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    if (!confirm('Delete this category? Transactions will remain but lose this category link.')) return;
    const id   = btn.dataset.id;
    const card = btn.closest('.cat-card');

    const fd = new FormData();
    fd.append('id', id);

    const res  = await fetch('/api/categories/delete', { method: 'POST', body: fd });
    const json = await res.json();

    if (json.success) {
      card.classList.add('removing');
      setTimeout(() => card.remove(), 300);
    } else {
      alert(json.message || 'Could not delete.');
    }
  });
});

// ── Search ────────────────────────────────────
document.getElementById('catSearch')?.addEventListener('input', function () {
  const q = this.value.toLowerCase();
  document.querySelectorAll('.cat-card').forEach(card => {
    card.style.display = card.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  });
});

// ── Filter tabs ───────────────────────────────
document.querySelectorAll('.notif-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.notif-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    const filter = tab.dataset.filter;
    document.querySelectorAll('.cat-card').forEach(card => {
      card.style.display =
        filter === 'all' || card.dataset.type === filter ? '' : 'none';
    });
  });
});
