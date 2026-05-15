/* ============================================================
   search.js — Global search overlay
   Taiwanese in Germany
   ============================================================ */

(function () {
  function initSearch() {
    const overlay = document.getElementById('searchOverlay');
    const input   = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    const openBtn = document.getElementById('searchBtn');
    const closeBtn = document.getElementById('searchClose');
    const sidebar = document.getElementById('sidebar');

    if (!overlay || !input) return;

    openBtn?.addEventListener('click', open);
    closeBtn?.addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') close();
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); open(); }
    });
    input.addEventListener('input', () => render(input.value.trim()));

    function open() {
      overlay.classList.add('open');
      sidebar?.classList.add('search-open');
      input.value = '';
      results.innerHTML = hint();
      setTimeout(() => input.focus(), 50);
    }

    function close() {
      overlay.classList.remove('open');
      sidebar?.classList.remove('search-open');
      input.blur();
    }

    function render(q) {
      if (!q) { results.innerHTML = hint(); return; }
      const lq = q.toLowerCase();
      const matched = POSTS.filter(p =>
        p.title.toLowerCase().includes(lq) ||
        p.excerpt.toLowerCase().includes(lq) ||
        p.categories.some(c => c.toLowerCase().includes(lq)) ||
        (p.tags || []).some(t => t.toLowerCase().includes(lq))
      ).slice(0, 8);

      if (!matched.length) { results.innerHTML = ''; return; }

      results.innerHTML = matched.map(p => `
        <a class="search-result" href="/posts/${p.slug}.html">
          <div class="search-result__emoji">${p.emoji}</div>
          <div class="search-result__body">
            <div class="search-result__title">${highlight(p.title, q)}</div>
            <div class="search-result__meta">${p.categories[0] || ''} · ${formatDate(p.date)}</div>
          </div>
        </a>
      `).join('');

      results.querySelectorAll('.search-result').forEach(el => {
        el.addEventListener('click', close);
      });
    }

    function highlight(text, q) {
      const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      return text.replace(re, '<mark>$1</mark>');
    }

    function hint() {
      return `<div class="search-hint">輸入關鍵字搜尋文章 · 支援標題、分類、標籤</div>`;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
  } else {
    initSearch();
  }
})();
