// Legacy ?slug=X URLs → /posts/<slug>.html (the canonical pre-rendered page).
// Runs as early as possible in post.html so the redirect is a single hop.
(function () {
  var slug = new URLSearchParams(window.location.search).get('slug');
  if (slug) window.location.replace('/posts/' + encodeURIComponent(slug) + '.html');
})();
