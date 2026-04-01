/* ============================================================
   theme.js — Location-aware automatic day/night theme
   Taiwanese in Germany
   ============================================================ */

const SVG_SUN  = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const SVG_MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

/* ---------- Sunrise / Sunset (USNO algorithm) ---------- */
// Returns { sunrise: Date|null, sunset: Date|null } in local time.
// null means polar day or polar night — caller defaults to light.
function getSunTimes(lat, lng) {
  const now = new Date();
  // Day of year (1–366)
  const N = Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000);
  const lngHour = lng / 15;

  const calcTime = (rising) => {
    const t = rising
      ? N + ((6  - lngHour) / 24)
      : N + ((18 - lngHour) / 24);

    // Sun's mean anomaly
    const M = (0.9856 * t) - 3.289;

    // Sun's true longitude
    let L = M + (1.916 * Math.sin(M * Math.PI / 180))
              + (0.020 * Math.sin(2 * M * Math.PI / 180))
              + 282.634;
    L = ((L % 360) + 360) % 360;

    // Sun's right ascension (hours)
    let RA = (180 / Math.PI) * Math.atan(0.91764 * Math.tan(L * Math.PI / 180));
    RA = ((RA % 360) + 360) % 360;
    RA = (RA + (Math.floor(L / 90) * 90 - Math.floor(RA / 90) * 90)) / 15;

    // Declination
    const sinDec = 0.39782 * Math.sin(L * Math.PI / 180);
    const cosDec = Math.cos(Math.asin(sinDec));

    // Local hour angle (zenith = 90.833° accounts for refraction + solar disc)
    const cosH = (Math.cos(90.833 * Math.PI / 180) - sinDec * Math.sin(lat * Math.PI / 180))
               / (cosDec * Math.cos(lat * Math.PI / 180));

    if (cosH >  1) return null; // always night
    if (cosH < -1) return null; // always day

    const H = rising
      ? (360 - (180 / Math.PI) * Math.acos(cosH)) / 15
      : ((180 / Math.PI) * Math.acos(cosH)) / 15;

    // Local mean time → UTC → local clock time
    const T  = H + RA - (0.06571 * t) - 6.622;
    const UT = ((T - lngHour) % 24 + 24) % 24;
    const localHours = UT - now.getTimezoneOffset() / 60;

    const d = new Date(now);
    d.setHours(0, 0, 0, 0);
    d.setTime(d.getTime() + localHours * 3600000);
    return d;
  };

  return { sunrise: calcTime(true), sunset: calcTime(false) };
}

function isNighttime(lat, lng) {
  const { sunrise, sunset } = getSunTimes(lat, lng);
  if (!sunrise || !sunset) return false; // polar edge case → keep light
  const now = new Date();
  return now < sunrise || now > sunset;
}

/* ---------- Apply Theme ---------- */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById('themeToggle');
  if (btn) btn.innerHTML = theme === 'dark' ? SVG_SUN : SVG_MOON;
}

/* ---------- Night Mode Toast ---------- */
function showNightToast() {
  if (sessionStorage.getItem('night_toast_shown')) return;
  sessionStorage.setItem('night_toast_shown', '1');

  const toast = document.createElement('div');
  toast.className = 'night-toast';
  toast.innerHTML = `
    <div class="night-toast__icon">🌙</div>
    <div class="night-toast__body">
      <div class="night-toast__title">夜間模式已開啟</div>
      <div class="night-toast__sub">依據您所在位置的日落時間自動調整</div>
      <div class="night-toast__actions">
        <button class="night-toast__btn" id="toastSwitchDay">切換白天模式</button>
        <button class="night-toast__close" id="toastClose">✕</button>
      </div>
    </div>
  `;
  document.body.appendChild(toast);

  const dismiss = () => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 350);
  };

  let autoTimer = setTimeout(dismiss, 6000);

  document.getElementById('toastSwitchDay').addEventListener('click', () => {
    clearTimeout(autoTimer);
    applyTheme('light');
    localStorage.setItem('theme', 'light');
    dismiss();
  });

  document.getElementById('toastClose').addEventListener('click', () => {
    clearTimeout(autoTimer);
    dismiss();
  });

  // Pause auto-dismiss while hovering
  toast.addEventListener('mouseenter', () => clearTimeout(autoTimer));
  toast.addEventListener('mouseleave', () => { autoTimer = setTimeout(dismiss, 3000); });
}

/* ---------- Toggle Button ---------- */
function handleToggleClick() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  localStorage.setItem('theme', next);
}

/* ---------- Init ---------- */
function initTheme() {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.addEventListener('click', handleToggleClick);

  // If the user has a manual preference saved, respect it and stop here
  const saved = localStorage.getItem('theme');
  if (saved) {
    applyTheme(saved);
    return;
  }

  // No manual preference: use cached location for instant theme, then refresh in background
  const cachedRaw = localStorage.getItem('theme_location');
  if (cachedRaw) {
    try {
      const { lat, lng } = JSON.parse(cachedRaw);
      const night = isNighttime(lat, lng);
      applyTheme(night ? 'dark' : 'light');
      if (night) showNightToast();
    } catch (e) {
      localStorage.removeItem('theme_location');
      // Fall through to system pref below
      const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      applyTheme(dark ? 'dark' : 'light');
    }
  } else {
    // First visit: apply system preference while waiting for geolocation
    const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(dark ? 'dark' : 'light');
  }

  // Async geolocation update
  if (!navigator.geolocation) return;

  navigator.geolocation.getCurrentPosition(
    ({ coords: { latitude: lat, longitude: lng } }) => {
      localStorage.setItem('theme_location', JSON.stringify({ lat, lng }));

      // Skip if user manually overrode while the geo request was in flight
      if (localStorage.getItem('theme')) return;

      const night = isNighttime(lat, lng);
      applyTheme(night ? 'dark' : 'light');

      // Show toast only on the first time we receive a live location result
      if (night && !cachedRaw) showNightToast();
    },
    () => { /* silently fall back to system pref already applied */ },
    { timeout: 8000, maximumAge: 600000 }
  );
}

document.addEventListener('DOMContentLoaded', initTheme);
