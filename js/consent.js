/* ============================================================
   consent.js — GDPR Cookie Consent (Google Analytics gating)
   德國知識小種子 Das deutsche Wissen

   Blocks GA until user explicitly accepts.
   Stores preference in localStorage ('cookie_consent').
   ============================================================ */

(function () {
  var GA_ID = 'G-2W0SLZF8LC';
  var STORAGE_KEY = 'cookie_consent'; // 'accepted' | 'rejected'

  /* ---------- Helpers ---------- */
  function getConsent() {
    return localStorage.getItem(STORAGE_KEY);
  }

  function setConsent(value) {
    localStorage.setItem(STORAGE_KEY, value);
  }

  /* ---------- Load GA dynamically ---------- */
  function loadGA() {
    if (document.getElementById('ga-script')) return;

    var s = document.createElement('script');
    s.id = 'ga-script';
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);

    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', GA_ID, { anonymize_ip: true });
  }

  /* ---------- Clear GA cookies ---------- */
  function clearGACookies() {
    var dominated = [location.hostname, '.' + location.hostname];
    document.cookie.split(';').forEach(function (c) {
      var name = c.split('=')[0].trim();
      if (name.startsWith('_ga') || name.startsWith('_gid')) {
        dominated.forEach(function (domain) {
          document.cookie = name + '=;expires=Thu,01 Jan 1970 00:00:00 GMT;path=/;domain=' + domain;
        });
        document.cookie = name + '=;expires=Thu,01 Jan 1970 00:00:00 GMT;path=/';
      }
    });
  }

  /* ---------- Banner UI ---------- */
  function showBanner() {
    if (document.getElementById('cookieConsent')) return;

    var banner = document.createElement('div');
    banner.id = 'cookieConsent';
    banner.className = 'cookie-banner';
    banner.innerHTML =
      '<div class="cookie-banner__inner">' +
        '<div class="cookie-banner__text">' +
          '<p class="cookie-banner__title">Cookie 使用通知</p>' +
          '<p class="cookie-banner__desc">' +
            '本站使用 Google Analytics Cookie 來分析訪客流量，以改善網站內容。' +
            '您的資料會以匿名方式處理。您可以隨時透過頁尾的「Cookie 設定」更改選擇。' +
          '</p>' +
        '</div>' +
        '<div class="cookie-banner__actions">' +
          '<button class="cookie-btn cookie-btn--accept" id="cookieAccept">接受</button>' +
          '<button class="cookie-btn cookie-btn--reject" id="cookieReject">拒絕</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(banner);
    requestAnimationFrame(function () {
      banner.classList.add('visible');
    });

    document.getElementById('cookieAccept').addEventListener('click', function () {
      setConsent('accepted');
      loadGA();
      hideBanner(banner);
    });

    document.getElementById('cookieReject').addEventListener('click', function () {
      setConsent('rejected');
      clearGACookies();
      hideBanner(banner);
    });
  }

  function hideBanner(banner) {
    banner.classList.remove('visible');
    banner.classList.add('hiding');
    setTimeout(function () { banner.remove(); }, 350);
  }

  /* ---------- Public: reopen consent dialog ---------- */
  window.openCookieSettings = function () {
    localStorage.removeItem(STORAGE_KEY);
    clearGACookies();
    showBanner();
  };

  /* ---------- Wire footer "Cookie 設定" button (CSP-safe) ---------- */
  function wireCookieSettingsButton() {
    var btn = document.getElementById('cookieSettingsBtn');
    if (btn) btn.addEventListener('click', window.openCookieSettings);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireCookieSettingsButton);
  } else {
    wireCookieSettingsButton();
  }

  /* ---------- Init ---------- */
  var consent = getConsent();

  if (consent === 'accepted') {
    loadGA();
  } else if (consent === 'rejected') {
    // Do nothing — respect user's choice
  } else {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }
})();
