/* ============================================================
   simple-page.js — 靜態單頁（404、隱私權聲明）的初始化
   德國知識小種子 Das deutsche Wissen

   這些頁面沒有文章列表，不需要 main.js／post-static.js，
   只要把主題切換接起來即可。CSP 禁止 inline script，
   所以初始化一律走這支外部檔案，不要寫回 <script> 區塊。
   ============================================================ */

(function () {
  function init() {
    if (typeof initTheme === 'function') initTheme();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
