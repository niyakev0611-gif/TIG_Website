# 德國知識小種子 — FB + IG + Threads 自動發文設定指南

用 `scripts/social-post.mjs` 把 `social/weekly/W{N}_posts.json` 的貼文透過 Meta Graph API 自動送出。
架構移植自 oasis 的 `fb-post.mjs`（`/Users/Lin/oasis/web/scripts/`），並擴充 Instagram 支援：

- **Facebook**：用 FB 內建排程（上傳 + 設定發布時間），到點由 FB 自動公開，腳本不用一直開著。
- **Instagram**：Graph API **不支援**未來排程，因此腳本在本機建 **launchd 一次性排程**，
  到點自動執行「IG 輪播立即發布」。Mac 屆時在睡眠 → 喚醒後會補跑（晚發不漏發）。
  IG 圖片只吃**公開 URL**：圖卡 PNG 必須先合進 main、GitHub Pages 部署完成後才能發 IG。
- **Threads**（2026/10 起）：獨立的 Threads API（`graph.threads.net`），**不在 Business Suite／
  粉專 token 底下**，要另外授權一次。一樣不支援未來排程 → 比照 IG 用 launchd 到點發輪播，
  發完自動在底下回覆第一則留言（放資料來源）。只有 posts.json 寫了 `threads_message` 的貼文才會發。

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

## Threads 一次性設定（2026/10 新增）

Threads 用的是**品牌 Threads 帳號本身的 OAuth token**（不是粉專 token），效期 60 天，
腳本會自動續期（每月 1、15 日的 launchd 排程＋每次發文前順手續），設定一次就好。

1. **先確認品牌 Threads 帳號存在，而且是「公開」帳號**：用品牌 IG 帳號登入 Threads App 建立個人檔案即可。
   ⚠️ 官方規定：私人帳號的授權 90 天後無法續期、必須重新授權——公開帳號才能靠自動續期一直用下去。
2. **Meta App 加上 Threads 使用案例**：`developers.facebook.com` → 既有的 TIG 社群自動化 App →
   使用案例新增 **「Access the Threads API」**（德文介面：Auf Threads API zugreifen）。
   後台的「Testing（測試）」步驟可以跳過——只有送 App 審查才需要。
3. **加權限**：左側 **使用案例（Use cases）** → Threads API → 自訂 →
   在 `threads_content_publish`、`threads_manage_replies` 旁按 **新增**（`threads_basic` 預設就有）。
4. **填網址**：左側選單 **Settings（設定）**，填完按 **Save**：
   - **回跳網址**（德文介面：Callback-URLs umleiten）：`https://taiwanese-in-germany.com/`
     ⚠️ 貼上後要**按 Enter** 讓網址變成小方塊，否則儲存會報「Bitte gib eine Redirect URI für OAuth an」。
     （結尾斜線要一致；如要用別的網址，在 `.env.local` 設 `THREADS_REDIRECT_URI`）
   - **Deauthorize callback URL** 與 **Data Deletion Requests URL**（德文：Callback-URL deinstallieren／löschen）：
     都填 `https://taiwanese-in-germany.com/privacy.html`
   - 這頁也有 **Threads app ID** 與 **Threads app secret**（⚠️ 用這一組，不是 App 基本設定裡的另一組），等一下要用。
5. **加測試者**：設定頁按 **Add or Remove Threads Test Users** → 應用程式角色 → 新增人員 →
   角色選 **Threads Tester** → 輸入品牌 Threads 帳號名稱。
   然後在 Threads（網頁版或 App）→ 設定 → 帳號 → **網站權限（Website permissions）→ 邀請** 接受邀請。
   （官方：有測試者角色的帳號隨時可授權，**不需要送 App 審查、也不需要發布 App**——只給自己用就維持開發模式。）
6. **產生 token（最簡單的方式）**：同一頁 Settings 下方的 **Nutzertoken-Generator**
   （使用者 token 產生器）→ 在品牌 Threads 帳號那一列按 **產生 token** → 複製。
   這就是 60 天效期的長效 token（⚠️ 只能替**公開**的 Threads 帳號產生）。
   貼進 repo 根目錄 `.env.local`（別貼進聊天、別 commit）：

```
THREADS_TOKEN=<剛剛複製的 token>
```

   第一次跑 `--check` 或發文時，腳本會自動查出帳號 ID 寫回 `.env.local`（`THREADS_USER_ID`），
   並安裝自動續期排程 `com.tig.threads-refresh`——之後不用再碰。

7. **（替代方式）OAuth 授權流程**：不想用後台產生器時才需要。先在 `.env.local` 填
   `THREADS_APP_ID`、`THREADS_APP_SECRET`（Settings 頁上方那一組），再跑：

```bash
node scripts/social-post.mjs --threads-auth
```

   - 打開印出的網址 → 用品牌 Threads 帳號登入 → 按「允許」
   - 瀏覽器會跳到 `https://taiwanese-in-germany.com/?code=…`（看到網站首頁是正常的）
   - 把**網址列整串**複製，貼進下一個指令（授權碼 1 小時內有效、只能用一次）：

```bash
node scripts/social-post.mjs --threads-auth "https://taiwanese-in-germany.com/?code=…"
```

8. **驗證**：`node scripts/social-post.mjs --check` → 應看到 `✓ Threads 帳號: @…` 與 24 小時發文額度。

> token 萬一過期（例如 Mac 關機超過 60 天沒續到）：重做步驟 6，產新 token 換進 `.env.local` 即可。

---

## 每週例行（全自動流程）

1. 週報 PR 合進 main、GitHub Pages 部署完成（約 30–60 秒）。
2. Claude 產生 `social/weekly/W{N}_posts.json`（FB 條列版 + IG 精簡版 + Threads 版 + 圖卡清單 + 排程時間）。
3. 預覽：`node scripts/social-post.mjs --week {N} --dry-run`
4. 排程：`node scripts/social-post.mjs --week {N}`
   - FB → 排進 FB 端，到點自動公開
   - IG → 排進本機 launchd，到點自動發輪播
   - Threads → 排進本機 launchd，到點自動發輪播＋自我回覆資料來源
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
node scripts/social-post.mjs --week 42 --threads              # 只排 Threads（FB/IG 已排過時用）
node scripts/social-post.mjs --week 42 --threads --now        # Threads 立刻發（測試用）
node scripts/social-post.mjs --threads-cancel w42-weekly      # 取消 Threads launchd 排程
node scripts/social-post.mjs --threads-refresh                # 手動續期 Threads token
```

平台旗標 `--fb`／`--ig`／`--threads` 可以併用（例：`--ig --threads`），都不加＝全部平台。
⚠️ FB 已排過的週次**不要再跑不帶旗標的指令**，否則 FB 會重複排一則；補排其他平台時加旗標。

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
- **Threads 上限**（Meta 官方文件）：每則 **500 字元**（emoji 以 UTF-8 位元組計，一個約佔 4 字元，
  腳本已用這個保守算法擋）；輪播 2–20 張；每則最多 5 個不同連結；每帳號 24 小時 250 則、回覆 1,000 則。
  圖片：JPEG／PNG、單張 ≤ 8 MB、寬 320–1440 px（1080×1080 圖卡約 0.4 MB，沒問題；腳本會擋超過 8 MB 的檔）。
  Threads 的連結**可以點**——主文一定要放網站週報連結，這是導流主力。
- **Threads 回覆**：`threads_reply` 在主文發出後自動回覆；回覆失敗只會警告，主文不會重發。
  記錄檔：`social/threads-post.log`、續期紀錄：`social/threads-refresh.log`。
- FB/IG token 過期／權限錯誤：重跑上面步驟 4 產新 token 換進 `.env.local` 即可。
