#!/usr/bin/env node
/*
  build.js — Static-site generator for taiwanese-in-germany.com

  Reads js/data.js (the single source of truth for posts), emits:
    posts/<slug>.html  — pre-rendered post page with full meta/OG/JSON-LD
    sitemap.xml        — regenerated from POSTS
    feed.xml           — RSS 2.0 feed of the 20 newest posts

  Run from repo root: node scripts/build.js
*/

import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '..');
const SITE = 'https://taiwanese-in-germany.com';
const SITE_NAME = '台勞在德國打工記';
const SITE_DESC = '台灣人在德國的生活記錄。分享來德生活必辦事項、德國日常、旅行攻略與德語學習。';
const AUTHOR = '台勞在德國';

// ---------- Load POSTS from data.js ----------
const dataSrc = fs.readFileSync(path.join(ROOT, 'js/data.js'), 'utf8');
const POSTS = (() => {
  const sandbox = {};
  const fn = new Function('module', 'globalThis', dataSrc.replace(/^const\s+POSTS\s*=/m, 'globalThis.POSTS ='));
  fn({}, sandbox);
  return sandbox.POSTS;
})();

console.log(`Loaded ${POSTS.length} posts from data.js`);

// ---------- Helpers ----------
function escapeAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeXml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}
function escapeJsonLd(s) {
  // Inside <script type="application/ld+json"> we just need to avoid </script> sequences
  return String(s).replace(/<\/(script)/gi, '<\\/$1');
}
function fmtDateZh(dateStr) {
  // 2026-05-11 -> 2026年5月11日
  const [y, m, d] = dateStr.split('-');
  return `${y}年${parseInt(m,10)}月${parseInt(d,10)}日`;
}

// Port of cleanWordPressContent from js/post.js (Node-safe)
function cleanWordPressContent(html) {
  return html
    .replace(/<!--\s*\/?wp:[\s\S]*?-->/g, '')
    .replace(/<p>\s*<\/p>/g, '')
    .replace(/‘|’/g, "'")
    .replace(/“|”/g, '"')
    .replace(/(&nbsp;){3,}/g, '&nbsp;')
    .trim();
}

// Rewrite relative asset paths to absolute so they work from /posts/<slug>.html
function rewriteAssetPaths(html) {
  return html
    .replace(/(\s(?:src|href)=")(?!https?:|\/\/|\/|#|mailto:|tel:|data:)/g, '$1/');
}

// Estimate reading minutes (350 Chinese chars per minute, matches post.js)
function readingTime(html) {
  const text = html.replace(/<[^>]+>/g, '');
  return Math.max(1, Math.round(text.length / 350));
}

// Find first <img src="..."> in the rendered content; return absolute URL or null
function firstImage(html) {
  const m = html.match(/<img\b[^>]*\bsrc="([^"]+)"/i);
  if (!m) return null;
  let src = m[1];
  if (/^https?:\/\//i.test(src)) return src;
  if (src.startsWith('/')) return SITE + src;
  return SITE + '/' + src;
}

// Compute up to 3 related posts (same category, exclude self)
function getRelated(post) {
  return POSTS
    .filter(p => p.slug !== post.slug && p.categories.some(c => post.categories.includes(c)))
    .slice(0, 3);
}

// ---------- Shared HTML chunks (copy verbatim from post.html so look/feel matches) ----------
const HEAD_CSP = `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://www.googletagmanager.com https://unpkg.com/@waline/; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com/@waline/; font-src 'self' https://fonts.gstatic.com https://unpkg.com/@waline/; img-src 'self' data: https:; connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://waline-server-lemon.vercel.app; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests" />`;

// Extract sidebar (hamburger + nav) and search overlay as separate, balanced blocks
const POST_SRC = fs.readFileSync(path.join(ROOT, 'post.html'), 'utf8');
function extractBlock(src, startMarker, endMarker) {
  const start = src.indexOf(startMarker);
  const end   = src.indexOf(endMarker, start + startMarker.length);
  if (start === -1 || end === -1) throw new Error(`Could not extract block: ${startMarker}`);
  return src.slice(start, end);
}
const HAMBURGER_BLOCK = extractBlock(POST_SRC, '<!-- MOBILE HAMBURGER -->', '<!-- SIDEBAR -->');
const SIDEBAR_BLOCK   = extractBlock(POST_SRC, '<!-- SIDEBAR -->',          '<!-- SEARCH OVERLAY -->');
const SEARCH_BLOCK    = extractBlock(POST_SRC, '<!-- SEARCH OVERLAY -->',   '<!-- POST -->');
const FOOTER_BLOCK    = extractBlock(POST_SRC, '<!-- FOOTER -->',           '<script src="js/data.js">');

function absolutizeLinks(html) {
  return html
    .replace(/href="index\.html"/g, 'href="/"')
    .replace(/href="category\.html/g, 'href="/category.html');
}
const SIDEBAR_ABS = absolutizeLinks(HAMBURGER_BLOCK + SIDEBAR_BLOCK + SEARCH_BLOCK);
const FOOTER_ABS  = absolutizeLinks(FOOTER_BLOCK);

// ---------- Render a single post ----------
function renderPost(post) {
  const cleanContent = rewriteAssetPaths(cleanWordPressContent(post.content));
  const canonical = `${SITE}/posts/${post.slug}.html`;
  const ogImageRaw = firstImage(cleanContent);
  const ogImage = ogImageRaw || `${SITE}/assets/og-default.png`;
  const twitterCardType = ogImageRaw ? 'summary_large_image' : 'summary';
  const fullTitle = `${post.title} | ${SITE_NAME}`;
  const desc = (post.excerpt || '').slice(0, 160);
  const mins = readingTime(cleanContent);
  const dateZh = fmtDateZh(post.date);
  const related = getRelated(post);
  const firstCat = post.categories[0] || '';

  const ldJson = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: desc,
    image: ogImage,
    url: canonical,
    datePublished: post.date,
    dateModified: post.date,
    author: { "@type": "Person", name: AUTHOR, url: SITE },
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE,
      logo: { "@type": "ImageObject", url: `${SITE}/assets/logo.png` }
    },
    mainEntityOfPage: { "@type": "WebPage", "@id": canonical },
    inLanguage: 'zh-TW',
    keywords: (post.tags || []).join(', ')
  };

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "首頁", item: SITE + '/' },
      ...(firstCat ? [{ "@type": "ListItem", position: 2, name: firstCat, item: `${SITE}/category.html?cat=${encodeURIComponent(firstCat)}` }] : []),
      { "@type": "ListItem", position: firstCat ? 3 : 2, name: post.title, item: canonical }
    ]
  };

  const catsHtml = post.categories.map(c =>
    `<a class="tag" href="/category.html?cat=${encodeURIComponent(c)}">${escapeAttr(c)}</a>`
  ).join('');

  const tagsHtml = (post.tags && post.tags.length)
    ? `<div class="post-tags" style="display:flex;"><span class="post-tags__label">標籤：</span>${
        post.tags.map(t => `<span class="tag tag--amber">${escapeAttr(t)}</span>`).join('')
      }</div>`
    : '';

  const relatedHtml = related.length
    ? `<div class="related"><h2 class="related__title">相關文章</h2><div class="related__grid">${
        related.map(rp => `<a class="post-card visible" href="/posts/${rp.slug}.html">
  <div class="post-card__cover" style="height:100px;font-size:2.5rem;">${escapeAttr(rp.emoji || '📝')}</div>
  <div class="post-card__body">
    <div class="post-card__title" style="-webkit-line-clamp:2;">${escapeAttr(rp.title)}</div>
    <div class="post-card__footer">
      <span class="post-card__date font-en">${fmtDateZh(rp.date)}</span>
      <span class="post-card__arrow">→</span>
    </div>
  </div>
</a>`).join('')
      }</div></div>`
    : '';

  const breadcrumbHtml = `
<nav class="breadcrumb" id="breadcrumb">
  <a href="/">首頁</a>
  <span class="breadcrumb__sep">›</span>
  ${firstCat ? `<a href="/category.html?cat=${encodeURIComponent(firstCat)}">${escapeAttr(firstCat)}</a>` : `<a href="/category.html">文章</a>`}
  <span class="breadcrumb__sep">›</span>
  <span>${escapeAttr(post.title.length > 30 ? post.title.slice(0,30) + '…' : post.title)}</span>
</nav>`;

  return `<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8" />
${HEAD_CSP}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<title>${escapeAttr(fullTitle)}</title>
<meta name="description" content="${escapeAttr(desc)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="${escapeAttr(canonical)}" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="${escapeAttr(SITE_NAME)}" />
<meta property="og:title" content="${escapeAttr(fullTitle)}" />
<meta property="og:description" content="${escapeAttr(desc)}" />
<meta property="og:url" content="${escapeAttr(canonical)}" />
<meta property="og:image" content="${escapeAttr(ogImage)}" />
<meta property="og:locale" content="zh_TW" />
<meta property="article:published_time" content="${escapeAttr(post.date)}" />
${(post.tags||[]).map(t => `<meta property="article:tag" content="${escapeAttr(t)}" />`).join('\n')}
<meta name="twitter:card" content="${twitterCardType}" />
<meta name="twitter:title" content="${escapeAttr(fullTitle)}" />
<meta name="twitter:description" content="${escapeAttr(desc)}" />
<meta name="twitter:image" content="${escapeAttr(ogImage)}" />
<script type="application/ld+json">${escapeJsonLd(JSON.stringify(ldJson))}</script>
<script type="application/ld+json">${escapeJsonLd(JSON.stringify(breadcrumbLd))}</script>
<link rel="stylesheet" href="/css/style.css" />
<link rel="stylesheet" href="https://unpkg.com/@waline/client@3.5.7/dist/waline.css" integrity="sha384-rRoXxn2yHlrZYB587Ki9RO1tONhLdM6XfORg7Rw4uwH4/Fh/5nP7IUX91bkaKUgs" crossorigin="anonymous" />
<link rel="alternate" type="application/rss+xml" title="${escapeAttr(SITE_NAME)} RSS" href="/feed.xml" />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🇩🇪</text></svg>" />
<script src="/js/consent.js"></script>
</head>
<body>
<div class="progress-bar" id="progressBar"></div>
${SIDEBAR_ABS}
<main class="post-layout" id="postLayout">
  <a href="/" class="back-btn" id="backBtn">← 返回</a>
  ${breadcrumbHtml}
  <header class="post-header" id="postHeader">
    <div class="post-header__cats">${catsHtml}</div>
    <h1 class="post-header__title">${escapeAttr(post.title)}</h1>
    <div class="post-header__meta">
      <span>${dateZh}</span>
      <span class="post-header__sep">·</span>
      <span>${mins} 分鐘閱讀</span>
    </div>
    <hr class="post-header__divider" />
  </header>
  <article class="post-content">${cleanContent}</article>
  ${tagsHtml}
  ${relatedHtml}
  <section class="comments-section" id="commentsSection">
    <h2 class="comments-section__title">留言</h2>
    <div id="waline"></div>
  </section>
</main>
${FOOTER_ABS}
<script src="/js/data.js"></script>
<script src="/js/theme.js"></script>
<script src="/js/search.js"></script>
<script src="/js/post-static.js"></script>
<script type="module" src="/js/waline-init.js"></script>
</body>
</html>
`;
}

// ---------- Sitemap ----------
function renderSitemap() {
  const urls = [];
  urls.push({ loc: `${SITE}/`, lastmod: POSTS[0].date, priority: '1.0', changefreq: 'weekly' });
  urls.push({ loc: `${SITE}/category.html`, lastmod: POSTS[0].date, priority: '0.8', changefreq: 'weekly' });

  // Categories — derive from POSTS
  const cats = new Set();
  POSTS.forEach(p => (p.categories || []).forEach(c => cats.add(c)));
  for (const c of cats) {
    const newest = POSTS.filter(p => p.categories.includes(c))
      .map(p => p.date).sort().pop();
    urls.push({
      loc: `${SITE}/category.html?cat=${encodeURIComponent(c)}`,
      lastmod: newest,
      priority: '0.7',
      changefreq: 'monthly'
    });
  }

  // Posts
  for (const p of POSTS) {
    urls.push({
      loc: `${SITE}/posts/${p.slug}.html`,
      lastmod: p.date,
      priority: '0.9',
      changefreq: p.slug === 'weekly-digest' ? 'weekly' : 'monthly'
    });
  }

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url>
    <loc>${escapeXml(u.loc)}</loc>
    <lastmod>${u.lastmod}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`).join('\n')}
</urlset>
`;
}

// ---------- RSS feed ----------
function renderFeed() {
  const items = [...POSTS]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, 20);

  const pubDate = new Date(items[0].date).toUTCString();

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <title>${escapeXml(SITE_NAME)}</title>
  <link>${SITE}/</link>
  <description>${escapeXml(SITE_DESC)}</description>
  <language>zh-TW</language>
  <lastBuildDate>${pubDate}</lastBuildDate>
  <atom:link href="${SITE}/feed.xml" rel="self" type="application/rss+xml" />
${items.map(p => {
  const url = `${SITE}/posts/${p.slug}.html`;
  const cleaned = cleanWordPressContent(p.content);
  return `  <item>
    <title>${escapeXml(p.title)}</title>
    <link>${url}</link>
    <guid isPermaLink="true">${url}</guid>
    <pubDate>${new Date(p.date).toUTCString()}</pubDate>
    <description>${escapeXml(p.excerpt || '')}</description>
    ${(p.categories||[]).map(c => `<category>${escapeXml(c)}</category>`).join('')}
    <content:encoded><![CDATA[${cleaned}]]></content:encoded>
  </item>`;
}).join('\n')}
</channel>
</rss>
`;
}

// ---------- Write files ----------
fs.mkdirSync(path.join(ROOT, 'posts'), { recursive: true });

let written = 0;
for (const post of POSTS) {
  const out = path.join(ROOT, 'posts', `${post.slug}.html`);
  fs.writeFileSync(out, renderPost(post));
  written++;
}
console.log(`Wrote ${written} static post pages → posts/*.html`);

fs.writeFileSync(path.join(ROOT, 'sitemap.xml'), renderSitemap());
console.log(`Wrote sitemap.xml (${POSTS.length} posts + categories + homepage)`);

fs.writeFileSync(path.join(ROOT, 'feed.xml'), renderFeed());
console.log(`Wrote feed.xml (${Math.min(POSTS.length, 20)} items)`);

console.log('Build complete.');
