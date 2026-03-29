/* ============================================================
   category.js — Category listing page
   Taiwanese in Germany
   ============================================================ */

function initTheme() {
  const btn = document.getElementById('themeToggle');
  if (!btn) return;
  const saved = localStorage.getItem('theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(saved);
  btn.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next); localStorage.setItem('theme', next);
  });
}
const SVG_SUN  = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const SVG_MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById('themeToggle');
  if (btn) btn.innerHTML = theme === 'dark' ? SVG_SUN : SVG_MOON;
}

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const activeCat = params.get('cat') || '';

  initNavbar();
  initTheme();
  initNavActive(activeCat);
  updateHero(activeCat);
  renderFilterBar(activeCat);
  renderPosts(activeCat);
  renderFooterLinks();
  initScrollReveal();
});

/* ---------- Sidebar ---------- */
function initNavbar() {
  const sidebar   = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const overlay   = document.getElementById('sidebarOverlay');

  hamburger.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    hamburger.classList.toggle('open', open);
    overlay.classList.toggle('visible', open);
  });

  overlay.addEventListener('click', closeSidebar);
  sidebar.querySelectorAll('.sidebar__link').forEach(link => {
    link.addEventListener('click', closeSidebar);
  });

  function closeSidebar() {
    sidebar.classList.remove('open');
    hamburger.classList.remove('open');
    overlay.classList.remove('visible');
  }
}

function initNavActive(activeCat) {
  document.querySelectorAll('.sidebar__link[data-cat]').forEach(link => {
    if (link.dataset.cat === activeCat) link.classList.add('active');
  });
}

/* ---------- Update Category Hero ---------- */
function updateHero(activeCat) {
  const catInfo   = CATEGORIES.find(c => c.name === activeCat);
  const titleEl   = document.getElementById('catTitle');
  const descEl    = document.getElementById('catDesc');
  const countEl   = document.getElementById('catCount');
  const pageTitle = document.getElementById('pageTitle');

  if (catInfo) {
    const count = getPostsByCategory(activeCat).length;
    titleEl.textContent   = catInfo.name;
    descEl.textContent    = catInfo.desc;
    countEl.textContent   = `共 ${count} 篇文章`;
    pageTitle.textContent = `${catInfo.name} | 台勞在德國打工記`;
  } else {
    titleEl.textContent = '所有文章';
    descEl.textContent  = '瀏覽全部文章';
    countEl.textContent = `共 ${POSTS.length} 篇文章`;
  }
}

/* ---------- Filter Bar ---------- */
function renderFilterBar(activeCat) {
  const bar = document.getElementById('filterBar');
  if (!bar) return;

  // "全部" button
  const allBtn = document.createElement('button');
  allBtn.className = 'filter-btn' + (!activeCat ? ' active' : '');
  allBtn.textContent = `全部 (${POSTS.length})`;
  allBtn.addEventListener('click', () => navigate(''));
  bar.appendChild(allBtn);

  CATEGORIES.forEach(cat => {
    const count = getPostsByCategory(cat.name).length;
    const btn = document.createElement('button');
    btn.className = 'filter-btn' + (activeCat === cat.name ? ' active' : '');
    btn.textContent = `${cat.emoji} ${cat.name} (${count})`;
    btn.addEventListener('click', () => navigate(cat.name));
    bar.appendChild(btn);
  });
}

function navigate(cat) {
  const url = cat
    ? `category.html?cat=${encodeURIComponent(cat)}`
    : 'category.html';
  window.location.href = url;
}

/* ---------- Render Posts ---------- */
function renderPosts(activeCat) {
  const grid  = document.getElementById('postsGrid');
  const empty = document.getElementById('emptyState');
  if (!grid) return;

  const posts = activeCat ? getPostsByCategory(activeCat) : POSTS;

  if (posts.length === 0) {
    grid.style.display = 'none';
    empty.style.display = 'block';
    return;
  }

  posts.forEach((post, i) => {
    const card = createPostCard(post, i);
    grid.appendChild(card);
  });
}

function createPostCard(post, index) {
  const a = document.createElement('a');
  a.className = 'post-card';
  a.href = `post.html?slug=${post.slug}`;
  a.dataset.delay = index * 60;

  const firstCat = post.categories[0] || '';

  a.innerHTML = `
    <div class="post-card__cover">${post.emoji}</div>
    <div class="post-card__body">
      <div class="post-card__cat">${firstCat}</div>
      <div class="post-card__title">${post.title}</div>
      <div class="post-card__excerpt">${post.excerpt}</div>
      <div class="post-card__footer">
        <span class="post-card__date">${formatDate(post.date)}</span>
        <span class="post-card__more">閱讀 →</span>
      </div>
    </div>
  `;
  return a;
}

/* ---------- Footer Links ---------- */
function renderFooterLinks() {
  const list = document.getElementById('footerLinks');
  if (!list) return;
  POSTS.slice(0, 5).forEach(post => {
    const li = document.createElement('li');
    const a  = document.createElement('a');
    a.href = `post.html?slug=${post.slug}`;
    a.className = 'footer__link';
    a.textContent = post.title.length > 22 ? post.title.slice(0, 22) + '…' : post.title;
    li.appendChild(a);
    list.appendChild(li);
  });
}

/* ---------- Scroll Reveal ---------- */
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = parseInt(entry.target.dataset.delay || 0);
        setTimeout(() => entry.target.classList.add('visible'), delay);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

  document.querySelectorAll('.post-card').forEach(card => observer.observe(card));
}
