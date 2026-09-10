/* =============================================
   AUTH PAGES — auth.js
   Shared JS for login.php & register.php
   ============================================= */

// ── Autofill credentials on click (for testing/demo) ──
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');

// Clear any pre-filled values on page load
if (emailInput) {
  emailInput.value = '';
}
if (passwordInput) {
  passwordInput.value = '';
}

if (emailInput) {
  emailInput.addEventListener('click', () => {
    if (!emailInput.value) {
      emailInput.value = 'test@example.com';
    }
  });
}

if (passwordInput) {
  passwordInput.addEventListener('click', () => {
    if (!passwordInput.value) {
      passwordInput.value = 'password123';
    }
  });
}

// ── Theme toggle (same logic as main.js) ─────
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

// ── Show / hide password toggle ───────────────
document.querySelectorAll('.toggle-pw').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    const icon  = btn.querySelector('i');
    if (input.type === 'password') {
      input.type  = 'text';
      icon.className = 'ri-eye-off-line';
    } else {
      input.type  = 'password';
      icon.className = 'ri-eye-line';
    }
  });
});

// ── Password strength meter (register only) ───
const pwInput  = document.getElementById('password');
const pwBar    = document.getElementById('pwBar');
const pwLabel  = document.getElementById('pwLabel');

if (pwInput && pwBar) {
  pwInput.addEventListener('input', () => {
    const val    = pwInput.value;
    const score  = getStrength(val);
    const levels = [
      { label: '',         color: '',          width: '0%'   },
      { label: 'Weak',     color: '#ef4444',   width: '25%'  },
      { label: 'Fair',     color: '#f59e0b',   width: '50%'  },
      { label: 'Good',     color: '#3b82f6',   width: '75%'  },
      { label: 'Strong',   color: '#10b981',   width: '100%' },
    ];
    const lvl = levels[score];
    pwBar.style.width      = lvl.width;
    pwBar.style.background = lvl.color;
    if (pwLabel) {
      pwLabel.textContent  = lvl.label;
      pwLabel.style.color  = lvl.color;
    }
  });
}

function getStrength(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8)              score++;
  if (/[A-Z]/.test(pw))            score++;
  if (/[0-9]/.test(pw))            score++;
  if (/[^A-Za-z0-9]/.test(pw))     score++;
  return score;
}

// ── Client-side form validation ───────────────
const registerForm = document.getElementById('registerForm');
const loginForm    = document.getElementById('loginForm');

if (registerForm) {
  registerForm.addEventListener('submit', (e) => {
    const name     = document.getElementById('full_name');
    const email    = document.getElementById('email');
    const password = document.getElementById('password');
    const confirm  = document.getElementById('confirm');
    const terms    = document.getElementById('terms');
    let   valid    = true;

    clearErrors();

    if (!name.value.trim() || name.value.trim().length < 2) {
      showError(name, 'Name must be at least 2 characters.');
      valid = false;
    } else if (!/^[a-zA-Z\s\-']+$/.test(name.value)) {
      showError(name, 'Name can only contain letters, spaces, hyphens, and apostrophes (no numbers).');
      valid = false;
    }

    if (!isValidEmail(email.value)) {
      showError(email, 'Enter a valid email address.');
      valid = false;
    }

    if (password.value.length < 8) {
      showError(password, 'Password must be at least 8 characters.');
      valid = false;
    }

    if (password.value !== confirm.value) {
      showError(confirm, 'Passwords do not match.');
      valid = false;
    }

    if (!terms.checked) {
      showError(terms, 'You must accept the terms.');
      valid = false;
    }

    if (!valid) e.preventDefault();
  });
}

if (loginForm) {
  loginForm.addEventListener('submit', (e) => {
    const email    = document.getElementById('email');
    const password = document.getElementById('password');
    let   valid    = true;

    clearErrors();

    if (!isValidEmail(email.value)) {
      showError(email, 'Enter a valid email address.');
      valid = false;
    }

    if (!password.value) {
      showError(password, 'Password is required.');
      valid = false;
    }

    if (!valid) e.preventDefault();
  });
}

// ── Helpers ───────────────────────────────────
function isValidEmail(val) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim());
}

function showError(input, msg) {
  // Mark input red
  const wrap = input.closest('.input-wrap') || input.closest('.form__group');
  const inp  = wrap ? wrap.querySelector('input') : input;
  if (inp) inp.classList.add('input--error');

  // Append inline error text
  const err = document.createElement('span');
  err.className   = 'inline-error';
  err.textContent = msg;
  err.style.cssText = 'font-size:.78rem;color:#ef4444;margin-top:.25rem;display:block;';

  const group = input.closest('.form__group');
  if (group && !group.querySelector('.inline-error')) {
    group.appendChild(err);
  }
}

function clearErrors() {
  document.querySelectorAll('.inline-error').forEach(el => el.remove());
  document.querySelectorAll('.input--error').forEach(el => el.classList.remove('input--error'));
}

// Clear error styling on input
document.querySelectorAll('.input-wrap input').forEach(input => {
  input.addEventListener('input', () => {
    input.classList.remove('input--error');
    const group = input.closest('.form__group');
    if (group) group.querySelector('.inline-error')?.remove();
  });
});

// ── Real-time name validation (prevent numbers) ──
const fullNameInput = document.getElementById('full_name');
if (fullNameInput) {
  fullNameInput.addEventListener('input', (e) => {
    // Remove any numbers from the input
    let value = e.target.value;
    const newValue = value.replace(/[0-9]/g, '');
    if (value !== newValue) {
      e.target.value = newValue;
    }
  });
  
  // Also prevent pasting numbers
  fullNameInput.addEventListener('paste', (e) => {
    e.preventDefault();
    const pastedText = (e.clipboardData || window.clipboardData).getData('text');
    const cleanedText = pastedText.replace(/[0-9]/g, '');
    document.execCommand('insertText', false, cleanedText);
  });
}
