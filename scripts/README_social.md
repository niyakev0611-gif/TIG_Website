# 德國知識小種子 — FB + IG 自動發文設定指南

用 `scripts/social-post.mjs` 把 `social/weekly/W{N}_posts.json` 的貼文透過 Meta Graph API 自動送出。
架構移植自 oasis 的 `fb-post.mjs`（`/Users/Lin/oasis/web/scripts/`），並擴充 Instagram 支援：

- **Facebook**：用 FB 內建排程（上傳 + 設定發布時間），到點由 FB 自動公開，腳本不用一直開著。
- **Instagram**：Graph API **不支援**未來排程，因此腳本在本機建 **launchd 一次性排程**，
  到點自動執行「IG 輪播立即發布」。Mac 屆時在睡眠 → 喚醒後會補跑（晚發不漏發）。
  IG 圖片只吃**公開 URL**：圖卡 PNG 必須先合進 main、GitHub Pages 部署完成後才能發 IG。

---

## 一次性設定（可直接沿用 oasis 的 Meta 設定）

oasis 那邊已經建好 Meta App（`oasis_automation`）與 System User（永不過期 token）。
TIG 這邊**不用重建 App**，只要把 TIG 的資產指派進去、產一顆新 token：

1. 到 `business.facebook.com` → 齒輪 **Einstellungen**（Business Settings）
   - 若「德國知識小種子」粉專和 oasis 不在同一個 Business Portfolio，先把粉專加進來
     （**Konten → Seiten → Hinzufügen**）。
2. **Konten → Instagram-Konten**：把品牌 IG 帳號加入，並確認它已在 IG App 內
   切成**商業帳號**且與粉專連結（IG App → 設定 → 商業工具與控制項 → 連結粉專）。
3. **Benutzer → Systembenutzer** → 選既有的 System User（如 `oasis-poster`）→
   **Assets zuweisen**：
   - 分頁 **Seiten** → 勾「德國知識小種子」→ 開「Inhalte verwalten」
   - 分頁 **Instagram-Konten** → 勾品牌 IG → 開內容管理
   - 分頁 **Apps** → 確認 App 已是 Vollzugriff
4. **Token generieren**：App 選同一個、有效期 **Nie**，權限勾：
   - `pages_show_list`、`pages_manage_posts`、`pages_read_engagement`
   - `instagram_basic`、`instagram_content_publish`
   - `business_management`（指派 IG 資產時通常需要）
5. 複製 token → 填進 repo 根目錄 `.env.local`（**別貼進聊天、別 commit**；`.env*` 已被 gitignore）：

```
FB_PAGE_ID=<德國知識小種子粉專的數字 ID>
FB_PAGE_TOKEN=<System User Token>
# IG_USER_ID 可不填，腳本會自動從粉專解析
```

6. 驗證：`node scripts/social-post.mjs --check`
   應顯示能管理「德國知識小種子」粉專，並列出 IG 帳號 `@…`。

> 找粉專 ID：Graph API Explorer 跑 `me/accounts?fields=id,name`，或粉專「關於」頁最下方。

---

## 每週例行（全自動流程）

1. 週報 PR 合進 main、GitHub Pages 部署完成（約 30–60 秒）。
2. Claude 產生 `social/weekly/W{N}_posts.json`（FB 條列版 + IG 精簡版 + 圖卡清單 + 排程時間）。
3. 預覽：`node scripts/social-post.mjs --week {N} --dry-run`
4. 排程：`node scripts/social-post.mjs --week {N}`
   - FB → 排進 FB 端，到點自動公開
   - IG → 排進本機 launchd，到點自動發輪播
5. 完成。不用再手動貼文。

## 常用指令

```bash
node scripts/social-post.mjs --week 28 --dry-run   # 預覽（不需 token）
node scripts/social-post.mjs --week 28             # FB 排程 + IG launchd 排程
node scripts/social-post.mjs --week 28 --fb        # 只 FB
node scripts/social-post.mjs --week 28 --ig --now  # IG 立刻發（測試用）
node scripts/social-post.mjs --check               # 診斷 token / 粉專 / IG
node scripts/social-post.mjs --list                # FB 端排程 + 本機 IG 排程
node scripts/social-post.mjs --move <fb_id> "2026-07-12 20:00"
node scripts/social-post.mjs --delete <fb_id>      # 刪 FB 排程（改文字＝先重排新的再刪舊的）
node scripts/social-post.mjs --ig-cancel w28-weekly  # 取消 IG launchd 排程
```

## 限制與注意

- **FB 排程時間**：需在「現在 +10 分鐘」到「+6 個月」之間；時間一律 Europe/Berlin 當地時間。
- **FB 不能原地編輯 API 排程貼文**：改文字流程 = 改 JSON → 重排新的 → `--delete` 舊的。
- **IG 上限**：輪播最多 10 張；文字 2,200 字元硬上限（腳本會擋），目標 ≤1,500；文內不放網址。
- **IG 圖片來源**：`images` 的 repo 相對路徑會自動轉成 `https://taiwanese-in-germany.com/...`，
  發 IG 前腳本會先 HEAD 檢查是否上線，沒上線會擋下並提示。
- **launchd 排程**：Mac 關機（非睡眠）期間到點的任務**不會**補跑；睡眠會在喚醒後補跑。
  發文日盡量讓 Mac 保持睡眠而非關機。記錄檔：`social/ig-post.log`。
- **排程貼文在哪看**：FB → 粉專 Professional-Dashboard → Inhalte → Planer
  （⚠️ Meta Business Suite 的 Planner 常不顯示 API 排的貼文，別慌）。
- token 過期／權限錯誤：重跑上面步驟 4 產新 token 換進 `.env.local` 即可。
