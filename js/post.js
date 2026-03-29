/* ============================================================
   post.js — Single post page
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
  const slug   = params.get('slug');

  initNavbar();
  initTheme();
  renderFooterLinks();

  if (!slug) {
    showNotFound();
    return;
  }

  const post = getPost(slug);
  if (!post) {
    showNotFound();
    return;
  }

  renderPost(post);
  initProgressBar();
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

/* ---------- Render Post ---------- */
function renderPost(post) {
  // <title> and meta
  document.getElementById('pageTitle').textContent   = `${post.title} | 台勞在德國打工記`;
  document.getElementById('metaDesc').setAttribute('content', post.excerpt);

  // Breadcrumb
  const firstCat = post.categories[0] || '';
  if (firstCat) {
    const catLink = document.getElementById('breadcrumbCat');
    catLink.href = `category.html?cat=${encodeURIComponent(firstCat)}`;
    catLink.textContent = firstCat;
  }
  document.getElementById('breadcrumbTitle').textContent =
    post.title.length > 30 ? post.title.slice(0, 30) + '…' : post.title;

  // Categories
  const catsEl = document.getElementById('postCats');
  post.categories.forEach(c => {
    const span = document.createElement('a');
    span.className = 'tag';
    span.href = `category.html?cat=${encodeURIComponent(c)}`;
    span.textContent = c;
    catsEl.appendChild(span);
  });

  // Title
  document.getElementById('postTitle').textContent = post.title;

  // Date
  document.getElementById('postDate').textContent = formatDate(post.date);

  // Reading time estimate (avg 350 Chinese chars/min)
  const plainText = post.content.replace(/<[^>]+>/g, '');
  const charCount = plainText.length;
  const minutes   = Math.max(1, Math.round(charCount / 350));
  document.getElementById('readingTime').textContent = `${minutes} 分鐘閱讀`;

  // Content — clean up WordPress shortcodes and render
  let html = cleanWordPressContent(post.content);
  document.getElementById('postContent').innerHTML = html;

  // Tags
  if (post.tags && post.tags.length > 0) {
    const tagsEl = document.getElementById('postTags');
    tagsEl.style.display = 'flex';
    post.tags.forEach(tag => {
      const span = document.createElement('span');
      span.className = 'tag tag--amber';
      span.textContent = tag;
      tagsEl.appendChild(span);
    });
  }

  // Related posts
  renderRelated(post);
}

/* ---------- Clean WordPress HTML ---------- */
function cleanWordPressContent(html) {
  return html
    // Remove Gutenberg block comments
    .replace(/<!-- \/?wp:[^\n]*?-->/g, '')
    // Remove empty paragraphs
    .replace(/<p>\s*<\/p>/g, '')
    // Linkify naked URLs (not already in href)
    // Fix WordPress curly quotes if any
    .replace(/\u2018|\u2019/g, "'")
    .replace(/\u201C|\u201D/g, '"')
    // Remove &nbsp; chains
    .replace(/(&nbsp;){3,}/g, '&nbsp;')
    .trim();
}

/* ---------- Related Posts ---------- */
function renderRelated(post) {
  const related = POSTS.filter(p =>
    p.slug !== post.slug &&
    p.categories.some(c => post.categories.includes(c))
  ).slice(0, 3);

  if (related.length === 0) return;

  const section = document.getElementById('related');
  const grid    = document.getElementById('relatedGrid');
  section.style.display = 'block';

  related.forEach(rp => {
    const a = document.createElement('a');
    a.className = 'post-card visible';
    a.href = `post.html?slug=${rp.slug}`;
    a.innerHTML = `
      <div class="post-card__cover" style="height:100px; font-size:2.5rem;">${rp.emoji}</div>
      <div class="post-card__body">
        <div class="post-card__title" style="-webkit-line-clamp:2;">${rp.title}</div>
        <div class="post-card__footer">
          <span class="post-card__date font-en">${formatDate(rp.date)}</span>
          <span class="post-card__arrow">→</span>
        </div>
      </div>
    `;
    grid.appendChild(a);
  });
}

/* ---------- Reading Progress Bar ---------- */
function initProgressBar() {
  const bar     = document.getElementById('progressBar');
  const content = document.getElementById('postContent');
  if (!bar || !content) return;

  function update() {
    const contentBottom = content.getBoundingClientRect().bottom + window.scrollY;
    const start  = content.getBoundingClientRect().top + window.scrollY - window.innerHeight;
    const total  = contentBottom - start - window.innerHeight;
    const scroll = window.scrollY - start;
    const pct    = Math.min(100, Math.max(0, (scroll / total) * 100));
    bar.style.width = pct + '%';
  }

  window.addEventListener('scroll', update, { passive: true });
  update();
}

/* ---------- 404 ---------- */
function showNotFound() {
  document.getElementById('postHeader').style.display = 'none';
  document.getElementById('breadcrumb').style.display = 'none';
  document.getElementById('notFound').style.display   = 'block';
  document.getElementById('pageTitle').textContent    = '找不到文章 | 台勞在德國打工記';
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
