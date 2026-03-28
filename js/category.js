/* ============================================================
   category.js — Category listing page
   Taiwanese in Germany
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const activeCat = params.get('cat') || '';

  initNavbar();
  initNavActive(activeCat);
  updateHero(activeCat);
  renderFilterBar(activeCat);
  renderPosts(activeCat);
  renderFooterLinks();
  initScrollReveal();
});

/* ---------- Navbar ---------- */
function initNavbar() {
  const hamburger = document.getElementById('hamburger');
  const navMenu = document.getElementById('navMenu');
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('open');
    navMenu.classList.toggle('open');
  });
}

function initNavActive(activeCat) {
  document.querySelectorAll('.navbar__link[data-cat]').forEach(link => {
    if (link.dataset.cat === activeCat) link.classList.add('active');
  });
}

/* ---------- Update Category Hero ---------- */
function updateHero(activeCat) {
  const catInfo = CATEGORIES.find(c => c.name === activeCat);
  const titleEl   = document.getElementById('catTitle');
  const descEl    = document.getElementById('catDesc');
  const emojiEl   = document.getElementById('catEmoji');
  const metaEl    = document.getElementById('catMeta');
  const breadEl   = document.getElementById('breadcrumbCurrent');
  const pageTitle = document.getElementById('pageTitle');

  if (catInfo) {
    const count = getPostsByCategory(activeCat).length;
    titleEl.textContent   = catInfo.name;
    descEl.textContent    = catInfo.desc;
    emojiEl.textContent   = catInfo.emoji;
    metaEl.textContent    = `共 ${count} 篇文章`;
    breadEl.textContent   = catInfo.name;
    pageTitle.textContent = `${catInfo.name} | 台勞在德國打工記`;
  } else {
    titleEl.textContent = '所有文章';
    descEl.textContent  = '瀏覽全部 ' + POSTS.length + ' 篇文章';
    emojiEl.textContent = '📝';
    metaEl.textContent  = `共 ${POSTS.length} 篇文章`;
    breadEl.textContent = '所有文章';
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

  const catsHtml = post.categories.map(c =>
    `<span class="tag">${c}</span>`
  ).join('');

  a.innerHTML = `
    <div class="post-card__cover">${post.emoji}</div>
    <div class="post-card__body">
      <div class="post-card__cats">${catsHtml}</div>
      <div class="post-card__title">${post.title}</div>
      <div class="post-card__excerpt">${post.excerpt}</div>
      <div class="post-card__footer">
        <span class="post-card__date font-en">${formatDate(post.date)}</span>
        <span class="post-card__arrow">→</span>
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
