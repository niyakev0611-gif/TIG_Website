#!/usr/bin/env node
/**
 * social-post.mjs — 德國知識小種子（Das deutsche Wissen）FB + IG + Threads 自動發文
 *
 * 移植自 oasis 的 fb-post.mjs，擴充 Instagram Content Publishing 與 Threads API 支援。
 * 把 social/weekly/W{N}_posts.json 裡的貼文，透過 Meta Graph API 送出
 * （單篇主題貼文放 social/{主題}/，用 --file 指定）：
 *
 *   Facebook  → 用 FB 內建排程（published=false + scheduled_publish_time），
 *               到點由 FB 自動公開，腳本不用一直開著。
 *   Instagram → Graph API「不支援」未來排程，因此：
 *               --now       立刻發（輪播 carousel，圖卡吃網站上的公開 URL）
 *               有 schedule 時自動建立 macOS launchd 一次性排程，
 *               到點在本機自動執行發文（Mac 睡著會在喚醒後補跑）。
 *   Threads   → 獨立的 Threads API（graph.threads.net），同樣不支援未來排程，
 *               比照 IG 用 launchd 到點發輪播；可另附一則自己回覆（放資料來源）。
 *               只有寫了 threads_message 的貼文才會發 Threads。
 *               憑證是 Threads 帳號的 OAuth token（60 天效期），
 *               腳本會自動續期（launchd 每月 1、15 日＋發文前順手續）。
 *
 * 貼文類型（type）：
 *   - "photo"        單張圖
 *   - "multi_photo"  多張圖一則（FB attached_media ／ IG carousel）
 * 沒寫 type 時：images 多張→multi_photo、其餘→photo。
 *
 * 用法（在 repo 根目錄執行）：
 *   node scripts/social-post.mjs --week 28 --dry-run     # 預覽（不需 token）
 *   node scripts/social-post.mjs --week 28               # FB 排程 + IG 建 launchd 排程
 *   node scripts/social-post.mjs --week 28 --fb          # 只處理 FB
 *   node scripts/social-post.mjs --week 28 --ig --now    # IG 立刻發
 *   node scripts/social-post.mjs --check                 # 診斷 token / 粉專 / IG 帳號
 *   node scripts/social-post.mjs --list                  # 列 FB 端排程 + 本機 IG launchd
 *   node scripts/social-post.mjs --move <fb_id> "YYYY-MM-DD HH:mm"
 *   node scripts/social-post.mjs --delete <fb_id>
 *   node scripts/social-post.mjs --ig-cancel <post_id>   # 取消某則 IG launchd 排程
 *   node scripts/social-post.mjs --week 42 --threads --now      # Threads 立刻發
 *   node scripts/social-post.mjs --threads-cancel <post_id>     # 取消某則 Threads 排程
 *   node scripts/social-post.mjs --threads-auth                 # 一次性授權：印出授權網址
 *   node scripts/social-post.mjs --threads-auth "<回跳網址>"     # 用回跳網址換長效 token
 *   node scripts/social-post.mjs --threads-refresh              # 手動續期 Threads token
 *
 *   平台旗標 --fb / --ig / --threads 可併用；都不加＝全部平台。
 *
 * 環境變數（repo 根目錄 .env.local，已被 .gitignore 封鎖）：
 *   FB_PAGE_ID       粉專數字 ID
 *   FB_PAGE_TOKEN    Page/System User Token
 *                    （FB：pages_manage_posts + pages_read_engagement + pages_show_list；
 *                      IG：再加 instagram_basic + instagram_content_publish）
 *   IG_USER_ID       （選填）IG 商業帳號 ID；不填會自動從粉專解析
 *   FB_API_VERSION   （選填）預設 v21.0
 *   SITE_BASE        （選填）預設 https://taiwanese-in-germany.com
 *   THREADS_APP_ID / THREADS_APP_SECRET   Meta App 的 Threads app ID／secret（授權時用）
 *   THREADS_REDIRECT_URI  （選填）預設 SITE_BASE + "/"，須與 App 設定完全一致
 *   THREADS_TOKEN / THREADS_USER_ID / THREADS_TOKEN_REFRESHED_AT
 *                    由 --threads-auth 自動寫入、--threads-refresh 自動更新，不用手填
 *
 * 一次性 token 設定教學：scripts/README_social.md
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");

// ── 讀 .env ───────────────────────────────────────────────────
function loadEnvFile(p) {
  if (!fs.existsSync(p)) return;
  for (const line of fs.readFileSync(p, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/i);
    if (!m) continue;
    let v = m[2];
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    if (!(m[1] in process.env)) process.env[m[1]] = v;
  }
}
loadEnvFile(path.join(REPO_ROOT, ".env.local"));
loadEnvFile(path.join(REPO_ROOT, ".env"));

const API_VERSION = process.env.FB_API_VERSION || "v21.0";
const PAGE_ID = process.env.FB_PAGE_ID;
let TOKEN = process.env.FB_PAGE_TOKEN;
let IG_USER_ID = process.env.IG_USER_ID || null;
const SITE_BASE = (process.env.SITE_BASE || "https://taiwanese-in-germany.com").replace(/\/$/, "");
const GRAPH = `https://graph.facebook.com/${API_VERSION}`;

const ENV_LOCAL = path.join(REPO_ROOT, ".env.local");
const THREADS_HOST = "https://graph.threads.net";
const THREADS_GRAPH = `${THREADS_HOST}/v1.0`;
const THREADS_APP_ID = process.env.THREADS_APP_ID;
const THREADS_APP_SECRET = process.env.THREADS_APP_SECRET;
const THREADS_REDIRECT_URI = process.env.THREADS_REDIRECT_URI || `${SITE_BASE}/`;
const THREADS_SCOPES = "threads_basic,threads_content_publish,threads_manage_replies";
let THREADS_TOKEN = process.env.THREADS_TOKEN || null;
let THREADS_USER_ID = process.env.THREADS_USER_ID || null;

// ── 參數 ──────────────────────────────────────────────────────
const args = process.argv.slice(2);
const DRY_RUN = args.includes("--dry-run");
const NOW = args.includes("--now");
const CHECK = args.includes("--check");
const LIST = args.includes("--list");
const FLAG_FB = args.includes("--fb");
const FLAG_IG = args.includes("--ig");
const FLAG_THREADS = args.includes("--threads");
const THREADS_AUTH = args.includes("--threads-auth");
const THREADS_REFRESH = args.includes("--threads-refresh");
function argAfter(flag, n = 1) {
  const i = args.indexOf(flag);
  const v = i >= 0 ? args[i + n] : null;
  return v && !v.startsWith("--") ? v : null;
}
const ONLY_ID = argAfter("--id");
const WEEK = argAfter("--week");
const FILE = argAfter("--file");
const MOVE_ID = argAfter("--move");
const MOVE_TIME = argAfter("--move", 2);
const DELETE_ID = argAfter("--delete");
const IG_CANCEL = argAfter("--ig-cancel");
const THREADS_CANCEL = argAfter("--threads-cancel");
const THREADS_AUTH_INPUT = argAfter("--threads-auth");

// 平台旗標可併用；都沒加＝全部平台
const anyPlatformFlag = FLAG_FB || FLAG_IG || FLAG_THREADS;
const doFB = !anyPlatformFlag || FLAG_FB;
const doIG = !anyPlatformFlag || FLAG_IG;
const doThreads = !anyPlatformFlag || FLAG_THREADS;

// ── Europe/Berlin 當地時間字串 → Unix 秒（自動處理夏令時） ────
function berlinOffsetMinutes(date) {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Berlin", hour12: false,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  const p = dtf.formatToParts(date).reduce((a, x) => { a[x.type] = x.value; return a; }, {});
  const asUTC = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
  return (asUTC - date.getTime()) / 60000;
}
function parseSchedule(str) {
  const m = String(str).match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})$/);
  if (!m) throw new Error(`schedule 格式錯誤（要 YYYY-MM-DD HH:mm）：${str}`);
  return m.slice(1).map(Number); // [y, mo, d, h, mi]
}
function berlinToUnix(str) {
  const [y, mo, d, h, mi] = parseSchedule(str);
  const utcGuess = Date.UTC(y, mo - 1, d, h, mi);
  const off = berlinOffsetMinutes(new Date(utcGuess));
  return Math.floor((utcGuess - off * 60000) / 1000);
}
function fmt(unix) {
  return new Date(unix * 1000).toLocaleString("de-DE", { timeZone: "Europe/Berlin" });
}

// ── 讀貼文資料 ────────────────────────────────────────────────
function resolvePostsFile() {
  if (FILE) return path.isAbsolute(FILE) ? FILE : path.join(REPO_ROOT, FILE);
  if (WEEK) return path.join(REPO_ROOT, "social", "weekly", `W${WEEK}_posts.json`);
  return null;
}
const POSTS_FILE = resolvePostsFile();
let posts = [];
if (POSTS_FILE) {
  if (!fs.existsSync(POSTS_FILE)) { console.error(`✋ 找不到貼文檔：${POSTS_FILE}`); process.exit(1); }
  const data = JSON.parse(fs.readFileSync(POSTS_FILE, "utf8"));
  posts = data.posts || [];
  if (ONLY_ID) {
    posts = posts.filter(p => p.id === ONLY_ID);
    if (!posts.length) { console.error(`找不到 id="${ONLY_ID}" 的貼文。`); process.exit(1); }
  }
}

const SIX_MONTHS = 60 * 60 * 24 * 30 * 6;
const TEN_MIN = 60 * 10;
const nowSec = Math.floor(Date.now() / 1000);
const IG_TEXT_LIMIT = 2200;
const THREADS_TEXT_LIMIT = 500;   // 官方：每則 500 字元，emoji 以 UTF-8 位元組數計
const THREADS_MAX_ITEMS = 20;     // 官方：輪播 2–20 張
const THREADS_MAX_LINKS = 5;      // 官方：每則最多 5 個不同連結

// ── 工具 ──────────────────────────────────────────────────────
function mediaAbs(rel) { return path.isAbsolute(rel) ? rel : path.join(REPO_ROOT, rel); }
function mediaUrl(rel) {
  // IG 只吃公開 URL：repo 相對路徑 → GitHub Pages 網址（PNG 需已合進 main 且部署完成）
  return `${SITE_BASE}/${rel.split(path.sep).join("/").split("/").map(encodeURIComponent).join("/")}`;
}
function postType(post) {
  if (post.type) return post.type;
  if (Array.isArray(post.images)) return post.images.length > 1 ? "multi_photo" : "photo";
  return "photo";
}
function collectMedia(post, rels = post.images || [post.image]) {
  rels = (rels || []).filter(Boolean);
  return rels.map(rel => {
    const abs = mediaAbs(rel);
    return { rel, abs, url: mediaUrl(rel), exists: fs.existsSync(abs) };
  });
}
async function graphPost(pathStr, form) {
  const res = await fetch(`${GRAPH}${pathStr}`, { method: "POST", body: form });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.error) throw new Error(`Graph API: ${JSON.stringify(json.error || json)}`);
  return json;
}
async function graphGet(pathStr) {
  const sep = pathStr.includes("?") ? "&" : "?";
  const res = await fetch(`${GRAPH}${pathStr}${sep}access_token=${TOKEN}`);
  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.error) throw new Error(`Graph API: ${JSON.stringify(json.error || json)}`);
  return json;
}
function fileBlob(abs) { return new Blob([fs.readFileSync(abs)]); }
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Threads 字數：一般字元算 1，emoji 依官方規則以 UTF-8 位元組數計（保守估算）
const EMOJI_RE = /[\p{Extended_Pictographic}\p{Regional_Indicator}\p{Emoji_Modifier}‍️⃣]/u;
function threadsTextLength(s) {
  let n = 0;
  for (const ch of s || "") n += EMOJI_RE.test(ch) ? Buffer.byteLength(ch, "utf8") : 1;
  return n;
}
function uniqueLinks(s) { return [...new Set((s || "").match(/https?:\/\/[^\s）)」]+/g) || [])]; }

// 把 key=value 寫回 .env.local（Threads token 續期用；保留其他內容、權限 600）
function updateEnvLocal(updates) {
  const lines = fs.existsSync(ENV_LOCAL) ? fs.readFileSync(ENV_LOCAL, "utf8").split(/\r?\n/) : [];
  for (const [k, v] of Object.entries(updates)) {
    const i = lines.findIndex(l => new RegExp(`^\\s*${k}\\s*=`).test(l));
    if (i >= 0) lines[i] = `${k}=${v}`; else lines.push(`${k}=${v}`);
    process.env[k] = v;
  }
  fs.writeFileSync(ENV_LOCAL, lines.join("\n").replace(/\n*$/, "\n"), { mode: 0o600 });
}

// ── Facebook 送出（與 oasis 相同機制） ────────────────────────
async function fbSendPhoto(post, scheduledUnix, message) {
  const abs = mediaAbs((post.images || [post.image])[0]);
  const form = new FormData();
  form.append("source", fileBlob(abs), path.basename(abs));
  form.append("caption", message);
  form.append("access_token", TOKEN);
  if (scheduledUnix) {
    form.append("published", "false");
    form.append("scheduled_publish_time", String(scheduledUnix));
  }
  const json = await graphPost(`/${PAGE_ID}/photos`, form);
  return json.post_id || json.id;
}
async function fbSendMultiPhoto(post, scheduledUnix, message) {
  const fbids = [];
  for (const rel of post.images) {
    const form = new FormData();
    form.append("source", fileBlob(mediaAbs(rel)), path.basename(rel));
    form.append("published", "false");
    form.append("access_token", TOKEN);
    const json = await graphPost(`/${PAGE_ID}/photos`, form);
    fbids.push(json.id);
  }
  const form = new FormData();
  form.append("message", message);
  form.append("access_token", TOKEN);
  fbids.forEach((id, i) => form.append(`attached_media[${i}]`, JSON.stringify({ media_fbid: id })));
  if (scheduledUnix) {
    form.append("published", "false");
    form.append("scheduled_publish_time", String(scheduledUnix));
  }
  const json = await graphPost(`/${PAGE_ID}/feed`, form);
  return json.id;
}

// ── Instagram 送出（Content Publishing API，只能立刻發） ──────
async function resolveIgUserId() {
  if (IG_USER_ID) return IG_USER_ID;
  const j = await graphGet(`/${PAGE_ID}?fields=instagram_business_account`);
  IG_USER_ID = j.instagram_business_account?.id;
  if (!IG_USER_ID) throw new Error("此粉專未連結 IG 商業帳號（或 token 缺 instagram_basic）。");
  return IG_USER_ID;
}
async function assertPublicUrl(url) {
  const res = await fetch(url, { method: "HEAD" }).catch(() => null);
  if (!res || !res.ok) {
    throw new Error(`圖片尚未公開上線：${url}\n  （IG／Threads 只吃公開 URL——PNG 要先合進 main、等 GitHub Pages 部署完成）`);
  }
}
async function igWaitReady(creationId) {
  for (let i = 0; i < 30; i++) {
    const j = await graphGet(`/${creationId}?fields=status_code,status`);
    if (j.status_code === "FINISHED") return;
    if (j.status_code === "ERROR") throw new Error(`IG container 處理失敗：${j.status || ""}`);
    await sleep(3000);
  }
  throw new Error("IG container 處理逾時（90 秒）。");
}
async function igPublish(post, caption) {
  await resolveIgUserId();
  const media = collectMedia(post);
  if (media.length > 10) throw new Error(`IG 輪播最多 10 張（目前 ${media.length} 張）。`);
  for (const m of media) await assertPublicUrl(m.url);

  let creationId;
  if (media.length === 1) {
    const form = new FormData();
    form.append("image_url", media[0].url);
    form.append("caption", caption);
    form.append("access_token", TOKEN);
    creationId = (await graphPost(`/${IG_USER_ID}/media`, form)).id;
  } else {
    const children = [];
    for (const m of media) {
      const form = new FormData();
      form.append("image_url", m.url);
      form.append("is_carousel_item", "true");
      form.append("access_token", TOKEN);
      children.push((await graphPost(`/${IG_USER_ID}/media`, form)).id);
    }
    const form = new FormData();
    form.append("media_type", "CAROUSEL");
    form.append("children", children.join(","));
    form.append("caption", caption);
    form.append("access_token", TOKEN);
    creationId = (await graphPost(`/${IG_USER_ID}/media`, form)).id;
  }
  await igWaitReady(creationId);
  const form = new FormData();
  form.append("creation_id", creationId);
  form.append("access_token", TOKEN);
  const json = await graphPost(`/${IG_USER_ID}/media_publish`, form);
  return json.id;
}

// ── Threads 送出（Threads API，只能立刻發） ─────────────────
async function threadsCall(method, pathStr, params = {}, base = THREADS_GRAPH) {
  const body = new URLSearchParams({ ...params, access_token: THREADS_TOKEN });
  const url = method === "GET" ? `${base}${pathStr}?${body}` : `${base}${pathStr}`;
  const res = await fetch(url, method === "GET" ? {} : { method, body });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.error) throw new Error(`Threads API: ${JSON.stringify(json.error || json)}`);
  return json;
}
function requireThreadsToken() {
  if (!THREADS_TOKEN || !THREADS_USER_ID) {
    throw new Error("缺 THREADS_TOKEN / THREADS_USER_ID——先跑 node scripts/social-post.mjs --threads-auth（教學見 scripts/README_social.md）。");
  }
}
async function threadsRefreshToken() {
  requireThreadsToken();
  const qs = new URLSearchParams({ grant_type: "th_refresh_token", access_token: THREADS_TOKEN });
  const res = await fetch(`${THREADS_HOST}/refresh_access_token?${qs}`);
  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.error || !json.access_token) throw new Error(`Threads token 續期失敗：${JSON.stringify(json.error || json)}`);
  THREADS_TOKEN = json.access_token;
  updateEnvLocal({ THREADS_TOKEN, THREADS_TOKEN_REFRESHED_AT: new Date().toISOString() });
  return Math.round((json.expires_in || 0) / 86400);
}
function threadsTokenAgeDays() {
  const t = Date.parse(process.env.THREADS_TOKEN_REFRESHED_AT || "");
  return Number.isFinite(t) ? (Date.now() - t) / 86400000 : null;
}
// 發文前順手續期：上次續期超過 7 天就續（官方要求 token 至少 24 小時才能續）
async function threadsMaybeRefresh() {
  const age = threadsTokenAgeDays();
  if (age !== null && age < 7) return;
  try {
    const days = await threadsRefreshToken();
    console.log(`  ↻ Threads token 已續期（效期 ${days} 天）`);
  } catch (e) { console.log(`  ⚠️ ${e.message}（先用現有 token 繼續）`); }
}
async function threadsWaitReady(containerId) {
  for (let i = 0; i < 60; i++) {   // 每 5 秒查一次，最多 5 分鐘
    const j = await threadsCall("GET", `/${containerId}`, { fields: "status,error_message" });
    if (j.status === "FINISHED") return;
    if (j.status === "ERROR" || j.status === "EXPIRED") throw new Error(`Threads container ${j.status}：${j.error_message || ""}`);
    await sleep(5000);
  }
  throw new Error("Threads container 處理逾時（5 分鐘）。");
}
async function threadsCreate(params) {
  return (await threadsCall("POST", `/${THREADS_USER_ID}/threads`, params)).id;
}
async function threadsPublishContainer(containerId) {
  await threadsWaitReady(containerId);
  return (await threadsCall("POST", `/${THREADS_USER_ID}/threads_publish`, { creation_id: containerId })).id;
}
async function threadsPublish(post, text, replyText) {
  requireThreadsToken();
  await threadsMaybeRefresh();
  const media = collectMedia(post, post.threads_images || post.images || [post.image]);
  if (media.length > THREADS_MAX_ITEMS) throw new Error(`Threads 輪播最多 ${THREADS_MAX_ITEMS} 張（目前 ${media.length} 張）。`);
  for (const m of media) await assertPublicUrl(m.url);

  let containerId;
  if (media.length === 0) {
    containerId = await threadsCreate({ media_type: "TEXT", text });
  } else if (media.length === 1) {
    containerId = await threadsCreate({ media_type: "IMAGE", image_url: media[0].url, text });
  } else {
    const children = [];
    for (const m of media) {
      children.push(await threadsCreate({ media_type: "IMAGE", image_url: m.url, is_carousel_item: "true" }));
    }
    for (const c of children) await threadsWaitReady(c);
    containerId = await threadsCreate({ media_type: "CAROUSEL", children: children.join(","), text });
  }
  const id = await threadsPublishContainer(containerId);

  // 自己回覆第一則（放資料來源）；主文已發出，回覆失敗只警告不重發
  let replyId = null;
  if (replyText) {
    try {
      const rc = await threadsCreate({ media_type: "TEXT", text: replyText, reply_to_id: id });
      replyId = await threadsPublishContainer(rc);
    } catch (e) { console.error(`  ⚠️ Threads 主文已發出，但自我回覆失敗：${e.message}`); }
  }
  return { id, replyId };
}

// ── Threads 一次性授權（OAuth → 長效 token → 寫入 .env.local） ──
async function threadsAuth(input) {
  if (!THREADS_APP_ID || !THREADS_APP_SECRET) {
    throw new Error("先在 .env.local 填 THREADS_APP_ID 與 THREADS_APP_SECRET（Meta App → 使用案例 Threads → 設定）。");
  }
  if (!input) {
    const qs = new URLSearchParams({
      client_id: THREADS_APP_ID, redirect_uri: THREADS_REDIRECT_URI,
      scope: THREADS_SCOPES, response_type: "code", state: "tig",
    });
    console.log("① 用瀏覽器打開下面網址，以品牌的 Threads 帳號登入並按「允許」：\n");
    console.log(`   https://threads.com/oauth/authorize?${qs}\n`);
    console.log(`② 瀏覽器會跳到 ${THREADS_REDIRECT_URI}?code=…，把網址列整串複製下來，再跑：\n`);
    console.log(`   node scripts/social-post.mjs --threads-auth "<剛剛複製的網址>"\n`);
    console.log("   （授權碼 1 小時內有效、只能用一次）");
    return;
  }
  let code = input.trim();
  if (/code=/.test(code)) code = new URL(code).searchParams.get("code") || "";
  code = code.replace(/#_?$/, "");
  if (!code) throw new Error("讀不到授權碼（code=…）。");

  // 授權碼 → 短效 token（1 小時）
  const res = await fetch(`${THREADS_HOST}/oauth/access_token`, {
    method: "POST",
    body: new URLSearchParams({
      client_id: THREADS_APP_ID, client_secret: THREADS_APP_SECRET,
      code, grant_type: "authorization_code", redirect_uri: THREADS_REDIRECT_URI,
    }),
  });
  const short = await res.json().catch(() => ({}));
  if (!res.ok || short.error || !short.access_token) throw new Error(`授權碼換 token 失敗：${JSON.stringify(short.error || short)}`);

  // 短效 → 長效 token（60 天）
  const qs = new URLSearchParams({ grant_type: "th_exchange_token", client_secret: THREADS_APP_SECRET, access_token: short.access_token });
  const res2 = await fetch(`${THREADS_HOST}/access_token?${qs}`);
  const long = await res2.json().catch(() => ({}));
  if (!res2.ok || long.error || !long.access_token) throw new Error(`換長效 token 失敗：${JSON.stringify(long.error || long)}`);

  THREADS_TOKEN = long.access_token;
  THREADS_USER_ID = String(short.user_id || "");
  const me = await threadsCall("GET", "/me", { fields: "id,username" });
  THREADS_USER_ID = String(me.id || THREADS_USER_ID);
  updateEnvLocal({ THREADS_TOKEN, THREADS_USER_ID, THREADS_TOKEN_REFRESHED_AT: new Date().toISOString() });
  console.log(`✅ Threads 授權完成：@${me.username}（${THREADS_USER_ID}），token 效期約 ${Math.round((long.expires_in || 0) / 86400)} 天，已寫入 .env.local`);
  const { label } = installThreadsRefreshJob();
  console.log(`✅ 已安裝自動續期排程（每月 1、15 日 10:00）：${label}`);
}

// ── 本機排程（macOS launchd 一次性任務，IG 與 Threads 共用） ──
// IG／Threads API 都不支援未來排程，所以在本機排 launchd：
// 到點自動跑「node social-post.mjs --ig|--threads --now --id <id>」，跑完自我移除。
// Mac 到點時在睡眠 → launchd 會在下次喚醒時補跑（會晚發，但不會漏發）。
const LAUNCHD = {
  ig: { prefix: "com.tig.igpost.", flag: "--ig", log: "ig-post.log", name: "IG" },
  threads: { prefix: "com.tig.threadspost.", flag: "--threads", log: "threads-post.log", name: "Threads" },
};
const THREADS_REFRESH_LABEL = "com.tig.threads-refresh";
function launchdLabel(platform, postId) { return `${LAUNCHD[platform].prefix}${postId.replace(/[^A-Za-z0-9.-]/g, "-")}`; }
function plistPath(label) { return path.join(os.homedir(), "Library", "LaunchAgents", `${label}.plist`); }
function xmlEscape(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
const shq = s => `'${s.replace(/'/g, `'\\''`)}'`;

function writeAndLoadPlist(label, cmd, calendarXml) {
  const plist = plistPath(label);
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${label}</string>
  <key>ProgramArguments</key><array>
    <string>/bin/zsh</string><string>-lc</string><string>${xmlEscape(cmd)}</string>
  </array>
  <key>StartCalendarInterval</key>${calendarXml}
  <key>RunAtLoad</key><false/>
</dict></plist>
`;
  // 先卸掉同名舊任務再重排（重跑腳本＝更新排程，不會重複發）
  try { execSync(`/bin/launchctl bootout gui/$(id -u)/${label} 2>/dev/null`); } catch {}
  fs.mkdirSync(path.dirname(plist), { recursive: true });
  fs.writeFileSync(plist, xml);
  execSync(`/bin/launchctl bootstrap gui/$(id -u) '${plist}'`);
  return { label, plist };
}
function scheduleLaunchd(platform, post, scheduleStr) {
  const [y, mo, d, h, mi] = parseSchedule(scheduleStr); // launchd 用本機時區＝Europe/Berlin
  const { flag, log } = LAUNCHD[platform];
  const label = launchdLabel(platform, post.id);
  const plist = plistPath(label);
  const logPath = path.join(REPO_ROOT, "social", log);
  const cmd = [
    `cd ${shq(REPO_ROOT)}`,
    `&& ${shq(process.execPath)} scripts/social-post.mjs ${flag} --now --file ${shq(POSTS_FILE)} --id ${shq(post.id)} >> ${shq(logPath)} 2>&1`,
    `; /bin/rm -f ${shq(plist)}`,
    `; /bin/launchctl bootout gui/$(id -u)/${label} 2>/dev/null`,
  ].join(" ");
  return writeAndLoadPlist(label, cmd, `<dict>
    <key>Year</key><integer>${y}</integer>
    <key>Month</key><integer>${mo}</integer>
    <key>Day</key><integer>${d}</integer>
    <key>Hour</key><integer>${h}</integer>
    <key>Minute</key><integer>${mi}</integer>
  </dict>`);
}
function installThreadsRefreshJob() {
  const logPath = path.join(REPO_ROOT, "social", "threads-refresh.log");
  const cmd = `cd ${shq(REPO_ROOT)} && ${shq(process.execPath)} scripts/social-post.mjs --threads-refresh >> ${shq(logPath)} 2>&1`;
  const day = n => `<dict><key>Day</key><integer>${n}</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>`;
  return writeAndLoadPlist(THREADS_REFRESH_LABEL, cmd, `<array>${day(1)}${day(15)}</array>`);
}
function listLaunchd(platform) {
  const dir = path.join(os.homedir(), "Library", "LaunchAgents");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.startsWith(LAUNCHD[platform].prefix)).map(f => f.replace(/\.plist$/, ""));
}
function cancelLaunchd(platform, postId) {
  const label = launchdLabel(platform, postId);
  try { execSync(`/bin/launchctl bootout gui/$(id -u)/${label} 2>/dev/null`); } catch {}
  fs.rmSync(plistPath(label), { force: true });
  return label;
}

// ── token 解析（User/System token → 該粉專 Page token） ───────
async function resolvePageToken() {
  const me = await graphGet(`/me?fields=id,name`);
  if (String(me.id) === String(PAGE_ID)) return TOKEN;
  const acc = await graphGet(`/me/accounts?fields=id,name,access_token`);
  const page = (acc.data || []).find(p => String(p.id) === String(PAGE_ID));
  if (!page || !page.access_token) throw new Error(`找不到 FB_PAGE_ID=${PAGE_ID} 的 Page token（token 要有 pages_show_list、且你是粉專管理員）。`);
  console.log(`✓ 已自動把 token 換成「${page.name}」的 Page token。`);
  return page.access_token;
}

// ── 單則處理 ──────────────────────────────────────────────────
// 沒寫 platforms 時：FB＋IG，有 threads_message 才加 Threads（舊貼文檔行為不變）
function platformsOf(post) {
  return post.platforms || ["fb", "ig", ...(post.threads_message ? ["threads"] : [])];
}
function previewText(label, text, maxLines = 8) {
  console.log(`  ── ${label} ──`);
  const lines = text.split("\n");
  console.log(lines.slice(0, maxLines).map(l => "  | " + l).join("\n") + (lines.length > maxLines ? "\n  | …" : ""));
}

async function processPost(post) {
  const type = postType(post);
  const fbMessage = post.fb_message || post.message || "";
  const igMessage = post.ig_message || post.message || "";
  const threadsMessage = post.threads_message || "";
  const threadsReply = post.threads_reply || "";
  const media = collectMedia(post);
  const threadsMedia = collectMedia(post, post.threads_images || post.images || [post.image]);
  const platforms = platformsOf(post);
  const wantFB = doFB && platforms.includes("fb");
  const wantIG = doIG && platforms.includes("ig");
  const wantThreads = doThreads && platforms.includes("threads");
  const fbScheduleStr = post.schedule || null;
  const igScheduleStr = post.ig_schedule || post.schedule || null;
  const threadsScheduleStr = post.threads_schedule || post.ig_schedule || post.schedule || null;
  const scheduledUnix = (!NOW && fbScheduleStr) ? berlinToUnix(fbScheduleStr) : null;

  // ── 預覽 ──
  console.log("\n────────────────────────────────────────────");
  console.log(`● ${post.id}  [${type}]  平台: ${[wantFB && "FB", wantIG && "IG", wantThreads && "Threads"].filter(Boolean).join(" + ") || "（無）"}`);
  for (const m of media) console.log(`  素材: ${m.rel} ${m.exists ? "✓" : "✗ (檔案不存在)"}`);
  if (wantFB) {
    console.log(NOW || !scheduledUnix ? "  FB: 立刻公開" : `  FB: 排程 ${fmt(scheduledUnix)} (Europe/Berlin)`);
    previewText("FB 文字", fbMessage);
  }
  if (wantIG) {
    console.log(NOW || !igScheduleStr ? "  IG: 立刻發布（輪播）" : `  IG: launchd 本機排程 ${igScheduleStr}（Mac 需屆時開機/可喚醒）`);
    const len = [...igMessage].length;
    console.log(`  IG 文長: ${len} 字元 ${len > IG_TEXT_LIMIT ? `✗ 超過 ${IG_TEXT_LIMIT} 上限！` : len > 1500 ? "⚠️ 超過 1500 安全值" : "✓"}`);
    if (/https?:\/\//.test(igMessage)) console.log("  ⚠️ IG 文內含網址（IG 連結不可點，建議刪除）");
  }
  const threadsProblems = [];
  if (wantThreads) {
    const kind = threadsMedia.length === 0 ? "純文字" : threadsMedia.length === 1 ? "單圖" : `輪播 ${threadsMedia.length} 張`;
    console.log(NOW || !threadsScheduleStr ? `  Threads: 立刻發布（${kind}）` : `  Threads: launchd 本機排程 ${threadsScheduleStr}（${kind}）`);
    if (!threadsMessage) threadsProblems.push("缺 threads_message");
    if (threadsMedia.length > THREADS_MAX_ITEMS) threadsProblems.push(`輪播超過 ${THREADS_MAX_ITEMS} 張`);
    for (const [label, text] of [["主文", threadsMessage], ["自我回覆", threadsReply]]) {
      if (!text) continue;
      const len = threadsTextLength(text);
      const links = uniqueLinks(text).length;
      console.log(`  Threads ${label}: ${len}/${THREADS_TEXT_LIMIT} 字元（emoji 依位元組計）· 連結 ${links} 個 ${len > THREADS_TEXT_LIMIT || links > THREADS_MAX_LINKS ? "✗" : len > 450 ? "⚠️ 接近上限" : "✓"}`);
      if (len > THREADS_TEXT_LIMIT) threadsProblems.push(`${label}超過 ${THREADS_TEXT_LIMIT} 字元`);
      if (links > THREADS_MAX_LINKS) threadsProblems.push(`${label}連結超過 ${THREADS_MAX_LINKS} 個`);
    }
    if (threadsMessage && !uniqueLinks(threadsMessage).length) console.log("  ⚠️ Threads 主文沒有網站連結（Threads 連結可點，建議放週報網址導流）");
    previewText("Threads 主文", threadsMessage, 40);
    if (threadsReply) previewText("Threads 自我回覆", threadsReply, 12);
  }

  if (DRY_RUN) { console.log("  [dry-run] 不送出。"); return; }

  // ── 驗證 ──
  const missing = [...media, ...(wantThreads ? threadsMedia : [])].filter(m => !m.exists);
  if (missing.length) throw new Error(`素材不存在：${[...new Set(missing.map(m => m.rel))].join(", ")}`);
  if (wantIG && [...igMessage].length > IG_TEXT_LIMIT) throw new Error(`IG 文字超過 ${IG_TEXT_LIMIT} 字元上限。`);
  if (wantThreads && threadsProblems.length) throw new Error(`Threads：${threadsProblems.join("、")}。`);
  if (wantFB && scheduledUnix) {
    if (scheduledUnix < nowSec + TEN_MIN) throw new Error(`FB 排程時間需在現在的 10 分鐘後（${fbScheduleStr}）。`);
    if (scheduledUnix > nowSec + SIX_MONTHS) throw new Error(`FB 排程時間不能超過 6 個月後（${fbScheduleStr}）。`);
  }

  // ── FB ──
  if (wantFB) {
    const sender = type === "multi_photo" ? fbSendMultiPhoto : fbSendPhoto;
    const id = await sender(post, scheduledUnix, fbMessage);
    console.log(`  ✅ FB 成功。id=${id || "?"}${scheduledUnix ? "（到點由 FB 自動公開）" : ""}`);
  }

  // ── IG ──
  if (wantIG) {
    if (NOW || !igScheduleStr) {
      const id = await igPublish(post, igMessage);
      console.log(`  ✅ IG 已發布。media_id=${id}`);
    } else {
      const { label } = scheduleLaunchd("ig", post, igScheduleStr);
      console.log(`  ✅ IG 已排 launchd：${igScheduleStr}（${label}）`);
      console.log(`     到點自動發、跑完自我移除；記錄在 social/ig-post.log`);
    }
  }

  // ── Threads ──
  if (wantThreads) {
    if (NOW || !threadsScheduleStr) {
      const { id, replyId } = await threadsPublish(post, threadsMessage, threadsReply);
      console.log(`  ✅ Threads 已發布。id=${id}${replyId ? `，自我回覆 id=${replyId}` : ""}`);
    } else {
      requireThreadsToken();
      const { label } = scheduleLaunchd("threads", post, threadsScheduleStr);
      console.log(`  ✅ Threads 已排 launchd：${threadsScheduleStr}（${label}）`);
      console.log(`     到點自動發、跑完自我移除；記錄在 social/threads-post.log`);
    }
  }
}

// ── 診斷 ──────────────────────────────────────────────────────
async function checkThreads() {
  if (!THREADS_TOKEN) { console.log("Threads：尚未授權（跑 --threads-auth）。"); return; }
  try {
    const me = await threadsCall("GET", "/me", { fields: "id,username" });
    console.log(`✓ Threads 帳號: @${me.username} → ${me.id}${String(me.id) !== String(THREADS_USER_ID) ? `（⚠️ 與 .env 的 THREADS_USER_ID=${THREADS_USER_ID} 不符）` : ""}`);
    const age = threadsTokenAgeDays();
    if (age !== null) console.log(`  token 上次續期：${age.toFixed(1)} 天前（60 天內沒續就會失效）`);
    const lim = await threadsCall("GET", `/${me.id}/threads_publishing_limit`, { fields: "quota_usage,config" });
    const q = (lim.data || [])[0];
    if (q) console.log(`  24 小時發文額度：已用 ${q.quota_usage} / ${q.config?.quota_total}`);
  } catch (e) { console.log(`⚠️ Threads 檢查: ${e.message}`); }
  const refreshJob = fs.existsSync(plistPath(THREADS_REFRESH_LABEL));
  console.log(`  自動續期排程：${refreshJob ? `✓ ${THREADS_REFRESH_LABEL}` : "✗ 未安裝（重跑 --threads-auth 或 --threads-refresh 會自動裝）"}`);
}

// ── 主流程 ────────────────────────────────────────────────────
(async () => {
  if (THREADS_AUTH) {
    try { await threadsAuth(THREADS_AUTH_INPUT); process.exit(0); }
    catch (e) { console.error(`❌ ${e.message}`); process.exit(1); }
  }

  if (THREADS_REFRESH) {
    try {
      const days = await threadsRefreshToken();
      console.log(`${new Date().toISOString()} ✅ Threads token 已續期，效期 ${days} 天。`);
      if (!fs.existsSync(plistPath(THREADS_REFRESH_LABEL))) installThreadsRefreshJob();
      process.exit(0);
    } catch (e) { console.error(`${new Date().toISOString()} ❌ ${e.message}`); process.exit(1); }
  }

  if (CHECK) {
    if (TOKEN) {
      const me = await graphGet(`/me?fields=id,name`).catch(e => ({ error: e.message }));
      if (me.error) console.error("FB Graph 回錯：", me.error);
      else {
        console.log("Token 對應身份：", me.id, me.name);
        console.log(".env 的 FB_PAGE_ID :", PAGE_ID);
        const acc = await graphGet(`/me/accounts?fields=id,name`).catch(() => ({ data: [] }));
        for (const p of acc.data || []) console.log(`  可管理粉專: ${p.name} → ${p.id}`);
        try {
          TOKEN = await resolvePageToken();
          const igId = await resolveIgUserId();
          const ig = await graphGet(`/${igId}?fields=username`);
          console.log(`✓ IG 商業帳號: @${ig.username} → ${igId}`);
        } catch (e) { console.log(`⚠️ IG 檢查: ${e.message}`); }
      }
    } else console.log("FB／IG：缺 FB_PAGE_TOKEN（.env.local）。");
    await checkThreads();
    for (const pf of ["ig", "threads"]) {
      const jobs = listLaunchd(pf);
      if (jobs.length) console.log(`本機 ${LAUNCHD[pf].name} launchd 排程：`, jobs.join(", "));
    }
    process.exit(0);
  }

  if (IG_CANCEL || THREADS_CANCEL) {
    const label = IG_CANCEL ? cancelLaunchd("ig", IG_CANCEL) : cancelLaunchd("threads", THREADS_CANCEL);
    console.log(`🗑️ 已取消 launchd 排程：${label}`);
    process.exit(0);
  }

  if (LIST) {
    if (TOKEN) {
      TOKEN = await resolvePageToken();
      const j = await graphGet(`/${PAGE_ID}/scheduled_posts?fields=id,scheduled_publish_time,message&limit=50`);
      const list = j.data || [];
      console.log(`FB 端 scheduled_posts：${list.length} 則`);
      for (const p of list) {
        const t = p.scheduled_publish_time ? fmt(p.scheduled_publish_time) : "?";
        console.log(`  - ${p.id}  ${t} · ${(p.message || "").slice(0, 36)}`);
      }
    }
    for (const pf of ["ig", "threads"]) {
      const jobs = listLaunchd(pf);
      console.log(`本機 ${LAUNCHD[pf].name} launchd 排程：${jobs.length} 則`);
      for (const l of jobs) console.log(`  - ${l}`);
    }
    process.exit(0);
  }

  if (MOVE_ID) {
    TOKEN = await resolvePageToken();
    const unix = berlinToUnix(MOVE_TIME);
    const form = new FormData();
    form.append("scheduled_publish_time", String(unix));
    form.append("access_token", TOKEN);
    await graphPost(`/${MOVE_ID}`, form);
    console.log(`✅ 已把 ${MOVE_ID} 改到 ${fmt(unix)} (Europe/Berlin)`);
    process.exit(0);
  }

  if (DELETE_ID) {
    TOKEN = await resolvePageToken();
    const res = await fetch(`${GRAPH}/${DELETE_ID}?access_token=${TOKEN}`, { method: "DELETE" });
    const j = await res.json().catch(() => ({}));
    if (j.error) { console.error(`❌ 刪除失敗：${JSON.stringify(j.error)}`); process.exit(1); }
    console.log(`🗑️ 已刪除 ${DELETE_ID}`);
    process.exit(0);
  }

  if (!POSTS_FILE) {
    console.error("✋ 請指定 --week <N> 或 --file <path>（貼文 JSON，見 scripts/social-posts.example.json）。");
    process.exit(1);
  }
  const needMeta = posts.some(p => platformsOf(p).some(x => (x === "fb" && doFB) || (x === "ig" && doIG)));
  const needThreads = posts.some(p => doThreads && platformsOf(p).includes("threads"));
  if (!DRY_RUN && needMeta && (!PAGE_ID || !TOKEN)) {
    console.error("✋ 缺少 FB_PAGE_ID / FB_PAGE_TOKEN（放 repo 根目錄 .env.local，教學見 scripts/README_social.md）。");
    console.error("   先跑 --dry-run 預覽不需要 token。");
    process.exit(1);
  }
  if (!DRY_RUN && needThreads && (!THREADS_TOKEN || !THREADS_USER_ID)) {
    console.error("✋ 缺少 THREADS_TOKEN / THREADS_USER_ID——先跑 node scripts/social-post.mjs --threads-auth（教學見 scripts/README_social.md）。");
    console.error("   只想發 FB／IG 可加 --fb --ig。");
    process.exit(1);
  }

  console.log(`德國知識小種子 社群發文 — ${DRY_RUN ? "DRY-RUN 預覽" : NOW ? "立即發布" : "排程模式"}`);
  console.log(`API: ${API_VERSION} · Page: ${PAGE_ID || "(dry-run)"} · 檔案: ${path.relative(REPO_ROOT, POSTS_FILE)} · 貼文數: ${posts.length}`);

  if (!DRY_RUN && needMeta) {
    try { TOKEN = await resolvePageToken(); }
    catch (e) { console.error(`✋ 取得 Page token 失敗：${e.message}`); process.exit(1); }
  }

  let fail = 0;
  for (const post of posts) {
    try { await processPost(post); }
    catch (e) { fail++; console.error(`  ❌ ${post.id} 失敗：${e.message}`); }
  }
  console.log("\n────────────────────────────────────────────");
  console.log(fail ? `完成，但有 ${fail} 則失敗。` : "全部完成。");
  if (!DRY_RUN && !NOW) {
    if (needMeta && doFB) console.log("FB：到點由 Facebook 自動公開（粉專 → Professional-Dashboard → Inhalte → Planer 可查）。");
    if (needMeta && doIG) console.log("IG：由本機 launchd 到點自動發（--list 可查、--ig-cancel <id> 可取消）。");
    if (needThreads) console.log("Threads：由本機 launchd 到點自動發（--list 可查、--threads-cancel <id> 可取消）。");
  }
  process.exit(fail ? 1 : 0);
})();
