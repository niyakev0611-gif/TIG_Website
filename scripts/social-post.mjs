#!/usr/bin/env node
/**
 * social-post.mjs — 德國知識小種子（Das deutsche Wissen）FB + IG 自動發文
 *
 * 移植自 oasis 的 fb-post.mjs，擴充 Instagram Content Publishing 支援。
 * 把 social/weekly/W{N}_posts.json 裡的貼文，透過 Meta Graph API 送出
 * （單篇主題貼文放 social/{主題}/，用 --file 指定）：
 *
 *   Facebook  → 用 FB 內建排程（published=false + scheduled_publish_time），
 *               到點由 FB 自動公開，腳本不用一直開著。
 *   Instagram → Graph API「不支援」未來排程，因此：
 *               --now       立刻發（輪播 carousel，圖卡吃網站上的公開 URL）
 *               有 schedule 時自動建立 macOS launchd 一次性排程，
 *               到點在本機自動執行發文（Mac 睡著會在喚醒後補跑）。
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
 *
 * 環境變數（repo 根目錄 .env.local，已被 .gitignore 封鎖）：
 *   FB_PAGE_ID       粉專數字 ID
 *   FB_PAGE_TOKEN    Page/System User Token
 *                    （FB：pages_manage_posts + pages_read_engagement + pages_show_list；
 *                      IG：再加 instagram_basic + instagram_content_publish）
 *   IG_USER_ID       （選填）IG 商業帳號 ID；不填會自動從粉專解析
 *   FB_API_VERSION   （選填）預設 v21.0
 *   SITE_BASE        （選填）預設 https://taiwanese-in-germany.com
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

// ── 參數 ──────────────────────────────────────────────────────
const args = process.argv.slice(2);
const DRY_RUN = args.includes("--dry-run");
const NOW = args.includes("--now");
const CHECK = args.includes("--check");
const LIST = args.includes("--list");
const FB_ONLY = args.includes("--fb");
const IG_ONLY = args.includes("--ig");
function argAfter(flag, n = 1) {
  const i = args.indexOf(flag);
  return i >= 0 ? args[i + n] : null;
}
const ONLY_ID = argAfter("--id");
const WEEK = argAfter("--week");
const FILE = argAfter("--file");
const MOVE_ID = argAfter("--move");
const MOVE_TIME = argAfter("--move", 2);
const DELETE_ID = argAfter("--delete");
const IG_CANCEL = argAfter("--ig-cancel");

const doFB = !IG_ONLY;
const doIG = !FB_ONLY;

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
function collectMedia(post) {
  const rels = (post.images || [post.image]).filter(Boolean);
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
    throw new Error(`圖片尚未公開上線：${url}\n  （IG 只吃公開 URL——PNG 要先合進 main、等 GitHub Pages 部署完成）`);
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

// ── IG 本機排程（macOS launchd 一次性任務） ───────────────────
// IG Graph API 不支援 scheduled_publish_time，所以在本機排 launchd：
// 到點自動跑「node social-post.mjs --ig --now --id <id>」，跑完自我移除。
// Mac 到點時在睡眠 → launchd 會在下次喚醒時補跑（會晚發，但不會漏發）。
function igLaunchdLabel(postId) { return `com.tig.igpost.${postId.replace(/[^A-Za-z0-9.-]/g, "-")}`; }
function igPlistPath(label) { return path.join(os.homedir(), "Library", "LaunchAgents", `${label}.plist`); }
function xmlEscape(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

function igScheduleLaunchd(post, scheduleStr) {
  const [y, mo, d, h, mi] = parseSchedule(scheduleStr); // launchd 用本機時區＝Europe/Berlin
  const label = igLaunchdLabel(post.id);
  const plist = igPlistPath(label);
  const logDir = path.join(REPO_ROOT, "social");
  const log = path.join(logDir, "ig-post.log");
  fs.mkdirSync(logDir, { recursive: true });
  const q = s => `'${s.replace(/'/g, `'\\''`)}'`;
  const cmd = [
    `cd ${q(REPO_ROOT)}`,
    `&& ${q(process.execPath)} scripts/social-post.mjs --ig --now --file ${q(POSTS_FILE)} --id ${q(post.id)} >> ${q(log)} 2>&1`,
    `; /bin/rm -f ${q(plist)}`,
    `; /bin/launchctl bootout gui/$(id -u)/${label} 2>/dev/null`,
  ].join(" ");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${label}</string>
  <key>ProgramArguments</key><array>
    <string>/bin/zsh</string><string>-lc</string><string>${xmlEscape(cmd)}</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Year</key><integer>${y}</integer>
    <key>Month</key><integer>${mo}</integer>
    <key>Day</key><integer>${d}</integer>
    <key>Hour</key><integer>${h}</integer>
    <key>Minute</key><integer>${mi}</integer>
  </dict>
  <key>RunAtLoad</key><false/>
</dict></plist>
`;
  // 先卸掉同名舊任務再重排（重跑腳本＝更新排程，不會重複發）
  try { execSync(`/bin/launchctl bootout gui/$(id -u)/${label} 2>/dev/null`); } catch {}
  fs.writeFileSync(plist, xml);
  execSync(`/bin/launchctl bootstrap gui/$(id -u) '${plist}'`);
  return { label, plist };
}
function igListLaunchd() {
  const dir = path.join(os.homedir(), "Library", "LaunchAgents");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.startsWith("com.tig.igpost.")).map(f => f.replace(/\.plist$/, ""));
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
async function processPost(post) {
  const type = postType(post);
  const fbMessage = post.fb_message || post.message || "";
  const igMessage = post.ig_message || post.message || "";
  const media = collectMedia(post);
  const platforms = post.platforms || ["fb", "ig"];
  const wantFB = doFB && platforms.includes("fb");
  const wantIG = doIG && platforms.includes("ig");
  const fbScheduleStr = post.schedule || null;
  const igScheduleStr = post.ig_schedule || post.schedule || null;
  const scheduledUnix = (!NOW && fbScheduleStr) ? berlinToUnix(fbScheduleStr) : null;

  // ── 預覽 ──
  console.log("\n────────────────────────────────────────────");
  console.log(`● ${post.id}  [${type}]  平台: ${[wantFB && "FB", wantIG && "IG"].filter(Boolean).join(" + ") || "（無）"}`);
  for (const m of media) console.log(`  素材: ${m.rel} ${m.exists ? "✓" : "✗ (檔案不存在)"}`);
  if (wantFB) {
    console.log(NOW || !scheduledUnix ? "  FB: 立刻公開" : `  FB: 排程 ${fmt(scheduledUnix)} (Europe/Berlin)`);
    console.log("  ── FB 文字 ──");
    console.log(fbMessage.split("\n").slice(0, 8).map(l => "  | " + l).join("\n") + (fbMessage.split("\n").length > 8 ? "\n  | …" : ""));
  }
  if (wantIG) {
    console.log(NOW || !igScheduleStr ? "  IG: 立刻發布（輪播）" : `  IG: launchd 本機排程 ${igScheduleStr}（Mac 需屆時開機/可喚醒）`);
    const len = [...igMessage].length;
    console.log(`  IG 文長: ${len} 字元 ${len > IG_TEXT_LIMIT ? `✗ 超過 ${IG_TEXT_LIMIT} 上限！` : len > 1500 ? "⚠️ 超過 1500 安全值" : "✓"}`);
    if (/https?:\/\//.test(igMessage)) console.log("  ⚠️ IG 文內含網址（IG 連結不可點，建議刪除）");
  }

  if (DRY_RUN) { console.log("  [dry-run] 不送出。"); return; }

  // ── 驗證 ──
  const missing = media.filter(m => !m.exists);
  if (missing.length) throw new Error(`素材不存在：${missing.map(m => m.rel).join(", ")}`);
  if (wantIG && [...igMessage].length > IG_TEXT_LIMIT) throw new Error(`IG 文字超過 ${IG_TEXT_LIMIT} 字元上限。`);
  if (scheduledUnix) {
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
      const { label } = igScheduleLaunchd(post, igScheduleStr);
      console.log(`  ✅ IG 已排 launchd：${igScheduleStr}（${label}）`);
      console.log(`     到點自動發、跑完自我移除；記錄在 social/ig-post.log`);
    }
  }
}

// ── 主流程 ────────────────────────────────────────────────────
(async () => {
  if (CHECK) {
    if (!TOKEN) { console.error("✋ 缺 FB_PAGE_TOKEN（.env.local）。"); process.exit(1); }
    const me = await graphGet(`/me?fields=id,name`).catch(e => ({ error: e.message }));
    if (me.error) { console.error("Graph 回錯：", me.error); process.exit(1); }
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
    const jobs = igListLaunchd();
    if (jobs.length) console.log("本機 IG launchd 排程：", jobs.join(", "));
    process.exit(0);
  }

  if (IG_CANCEL) {
    const label = igLaunchdLabel(IG_CANCEL);
    try { execSync(`/bin/launchctl bootout gui/$(id -u)/${label} 2>/dev/null`); } catch {}
    fs.rmSync(igPlistPath(label), { force: true });
    console.log(`🗑️ 已取消 IG launchd 排程：${label}`);
    process.exit(0);
  }

  if (LIST) {
    TOKEN = await resolvePageToken();
    const j = await graphGet(`/${PAGE_ID}/scheduled_posts?fields=id,scheduled_publish_time,message&limit=50`);
    const list = j.data || [];
    console.log(`FB 端 scheduled_posts：${list.length} 則`);
    for (const p of list) {
      const t = p.scheduled_publish_time ? fmt(p.scheduled_publish_time) : "?";
      console.log(`  - ${p.id}  ${t} · ${(p.message || "").slice(0, 36)}`);
    }
    const jobs = igListLaunchd();
    console.log(`本機 IG launchd 排程：${jobs.length} 則`);
    for (const l of jobs) console.log(`  - ${l}`);
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
  if (!DRY_RUN && (!PAGE_ID || !TOKEN)) {
    console.error("✋ 缺少 FB_PAGE_ID / FB_PAGE_TOKEN（放 repo 根目錄 .env.local，教學見 scripts/README_social.md）。");
    console.error("   先跑 --dry-run 預覽不需要 token。");
    process.exit(1);
  }

  console.log(`德國知識小種子 社群發文 — ${DRY_RUN ? "DRY-RUN 預覽" : NOW ? "立即發布" : "排程模式"}`);
  console.log(`API: ${API_VERSION} · Page: ${PAGE_ID || "(dry-run)"} · 檔案: ${path.relative(REPO_ROOT, POSTS_FILE)} · 貼文數: ${posts.length}`);

  if (!DRY_RUN) {
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
    console.log("FB：到點由 Facebook 自動公開（粉專 → Professional-Dashboard → Inhalte → Planer 可查）。");
    console.log("IG：由本機 launchd 到點自動發（--list 可查、--ig-cancel <id> 可取消）。");
  }
  process.exit(fail ? 1 : 0);
})();
