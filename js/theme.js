/* ============================================================
   theme.js — System preference-aware day/night theme
   Taiwanese in Germany
   ============================================================ */

const SVG_SUN  = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const SVG_MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

/* ---------- Apply Theme ---------- */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById('themeToggle');
  if (btn) btn.innerHTML = theme === 'dark' ? SVG_SUN : SVG_MOON;
}

/* ---------- Toggle Button ---------- */
function handleToggleClick() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  localStorage.setItem('theme', next);
}

/* ---------- First-Visit Hint Toast ---------- */
function showFirstVisitToast() {
  if (localStorage.getItem('hint_shown')) return;
  localStorage.setItem('hint_shown', '1');

  const toast = document.createElement('div');
  toast.className = 'night-toast';
  toast.innerHTML = `
    <div class="night-toast__icon">🌓</div>
    <div class="night-toast__body">
      <div class="night-toast__title">可以自由切換深色／淺色模式</div>
      <div class="night-toast__sub">點選左側選單底部的按鈕即可切換</div>
    </div>
    <button class="night-toast__close" id="hintClose">✕</button>
  `;
  document.body.appendChild(toast);

  const dismiss = () => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 350);
  };

  let autoTimer = setTimeout(dismiss, 5000);
  document.getElementById('hintClose').addEventListener('click', () => {
    clearTimeout(autoTimer);
    dismiss();
  });
  toast.addEventListener('mouseenter', () => clearTimeout(autoTimer));
  toast.addEventListener('mouseleave', () => { autoTimer = setTimeout(dismiss, 3000); });
}

/* ---------- Init ---------- */
function initTheme() {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.addEventListener('click', handleToggleClick);

  // Clean up legacy location cache
  localStorage.removeItem('theme_location');

  // If the user has a manual preference saved, respect it
  const saved = localStorage.getItem('theme');
  if (saved) {
    applyTheme(saved);
    return;
  }

  // Follow system/browser preference (no location permission needed)
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  applyTheme(prefersDark.matches ? 'dark' : 'light');

  // Show hint to first-time visitors
  showFirstVisitToast();

  // Live-update if system preference changes (e.g. OS auto dark mode)
  prefersDark.addEventListener('change', e => {
    if (!localStorage.getItem('theme')) {
      applyTheme(e.matches ? 'dark' : 'light');
    }
  });
}

// initTheme() is called by each page's own DOMContentLoaded handler
// (main.js, post.js, category.js) — do NOT auto-init here to avoid
// double-binding the toggle click listener.
