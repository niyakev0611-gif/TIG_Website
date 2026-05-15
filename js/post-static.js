/* ============================================================
   post-static.js — interactivity for pre-rendered post pages
   Content / meta / related are already in HTML; this file
   only wires up sidebar, theme, back button, progress bar,
   and footer recent-posts list.
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initTheme();
  initBackButton();
  initProgressBar();
  renderFooterLinks();
});

function initNavbar() {
  const sidebar   = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const overlay   = document.getElementById('sidebarOverlay');
  if (!sidebar || !hamburger || !overlay) return;

  hamburger.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    hamburger.classList.toggle('open', open);
    overlay.classList.toggle('visible', open);
  });
  overlay.addEventListener('click', closeSidebar);
  sidebar.querySelectorAll('.sidebar__link').forEach(l => l.addEventListener('click', closeSidebar));

  function closeSidebar() {
    sidebar.classList.remove('open');
    hamburger.classList.remove('open');
    overlay.classList.remove('visible');
  }
}

function initBackButton() {
  const btn = document.getElementById('backBtn');
  if (!btn) return;
  btn.addEventListener('click', (e) => {
    if (window.history.length > 1) {
      e.preventDefault();
      history.back();
    }
  });
}

function initProgressBar() {
  const bar = document.getElementById('progressBar');
  const content = document.querySelector('.post-content');
  if (!bar || !content) return;
  function update() {
    const rect = content.getBoundingClientRect();
    const contentBottom = rect.bottom + window.scrollY;
    const start = rect.top + window.scrollY - window.innerHeight;
    const total = contentBottom - start - window.innerHeight;
    if (total <= 0) { bar.style.width = '0%'; return; }
    const scroll = window.scrollY - start;
    const pct = Math.min(100, Math.max(0, (scroll / total) * 100));
    bar.style.width = pct + '%';
  }
  window.addEventListener('scroll', update, { passive: true });
  update();
}

function renderFooterLinks() {
  const list = document.getElementById('footerLinks');
  if (!list || typeof POSTS === 'undefined') return;
  POSTS.slice(0, 5).forEach(p => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = `/posts/${p.slug}.html`;
    a.className = 'footer__link';
    a.textContent = p.title.length > 22 ? p.title.slice(0, 22) + '…' : p.title;
    li.appendChild(a);
    list.appendChild(li);
  });
}
