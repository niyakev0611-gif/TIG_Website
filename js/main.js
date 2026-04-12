/* ============================================================
   main.js — Home page logic
   Taiwanese in Germany
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initTheme();
  renderCategories();
  renderRecentPosts();
  renderFooterLinks();
  initScrollReveal();
});

/* ---------- Sidebar ---------- */
function initNavbar() {
  const sidebar  = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const overlay  = document.getElementById('sidebarOverlay');

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

/* ---------- Render Category Cards ---------- */
function renderCategories() {
  const grid = document.getElementById('categoriesGrid');
  if (!grid) return;

  CATEGORIES.forEach(cat => {
    const count = getPostsByCategory(cat.name).length;
    const card = document.createElement('a');
    card.className = 'cat-card';
    card.href = `category.html?cat=${encodeURIComponent(cat.name)}`;
    card.innerHTML = `
      <div class="cat-card__emoji">${cat.emoji}</div>
      <div class="cat-card__name">${cat.name}</div>
      <div class="cat-card__desc">${cat.desc}</div>
      <div class="cat-card__count">${count} 篇文章</div>
    `;
    grid.appendChild(card);
  });
}

/* ---------- Render Recent Posts Grid ---------- */
function renderRecentPosts() {
  const grid = document.getElementById('postsGrid');
  if (!grid) return;

  const recent = POSTS.slice(0, 6);
  recent.forEach(post => {
    const card = createPostCard(post);
    grid.appendChild(card);
  });
}

/* ---------- Post Card Factory ---------- */
function createPostCard(post) {
  const a = document.createElement('a');
  a.className = 'post-card';
  a.href = `post.html?slug=${post.slug}`;

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

/* ---------- Footer Recent Links ---------- */
function renderFooterLinks() {
  const list = document.getElementById('footerLinks');
  if (!list) return;
  POSTS.slice(0, 5).forEach(post => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = `post.html?slug=${post.slug}`;
    a.className = 'footer__link';
    a.textContent = post.title.length > 22 ? post.title.slice(0, 22) + '…' : post.title;
    li.appendChild(a);
    list.appendChild(li);
  });
}

/* ---------- Scroll Reveal (IntersectionObserver) ---------- */
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  // Observe .reveal elements
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  // Observe post cards with stagger
  const cardObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        const delay = parseInt(entry.target.dataset.delay || 0);
        setTimeout(() => {
          entry.target.classList.add('visible');
        }, delay);
        cardObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

  document.querySelectorAll('.post-card').forEach((card, i) => {
    card.dataset.delay = i * 80;
    cardObserver.observe(card);
  });

  // Cat cards stagger via CSS already, just trigger visibility
  const catObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.closest('.categories-grid')
          ?.querySelectorAll('.cat-card')
          .forEach((c, i) => {
            setTimeout(() => c.classList.add('visible'), i * 80);
          });
        catObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  const catGrid = document.getElementById('categoriesGrid');
  if (catGrid) catObserver.observe(catGrid);
}
