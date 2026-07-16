# CLAUDE.md — 德國知識小種子 Das deutsche Wissen

本檔為 Claude Code 在此 repo 工作時的長期記憶與品牌守則。每個 session 開啟時都會自動讀取。

---

## 🧭 True North —— 全流程自動化（用戶 2026/07 定調）

**本專案的主旨：一切以自動化為目標，讓每週產出到發布完全不需要用戶手動操作。**

- 內容產出自動化：圖卡（Pillow）、`js/data.js`、靜態頁 build、FB/IG 雙版貼文——一次全部備齊。
- **社群發布自動化（2026/07 起）**：FB 與 IG 貼文一律走 Meta Graph API 排程
  （`scripts/social-post.mjs`，比照 oasis 的 `fb-post.mjs` 架構），**不再手動貼文**。
  FB 用原生排程、IG 用本機 launchd 到點自動發。詳見 `scripts/README_social.md`。
- 遇到還在手動做的重複步驟，主動提出並實作自動化方案。
- **內容飛輪（用戶 2026/07 定調）**：每次做圖卡與 FB/IG 貼文時，**盡可能帶入網站既有文章**——
  有相關或類似主題就加「📖 延伸閱讀：這篇你可能會喜歡」導流舊文，放大既有內容的效果；
  FB/IG 發文內容要與網站已公開文章**緊緊相扣**（同源一致、互相導流）。
- **舊文查核**：帶入或引用舊文前，先查核內容是否仍屬實；需要就更新，並在 `js/data.js`
  該文加 `updated: 'YYYY-MM-DD'`（build.js 會顯示「發布＋更新」雙時間標記、寫入
  sitemap lastmod 與 article:modified_time）。網站文章盡可能都打上時間標記。
- **圖卡視覺升級（用戶 2026/07 要求；W29 起為固定流程）**：不要純文字牆——**每張週報圖卡
  都必須含一個「Seedling Flat」扁平風精緻插畫**（Pillow 畫幾何圖形：粗深藍描邊 #1F2937、
  品牌配色填充、2x 超取樣抗鋸齒）。產圖一律用 `scripts/cardgen/make_weekly_cards.py`
  （版型＋插畫元件庫），設計哲學見 `scripts/cardgen/design_philosophy_seedling_flat.md`。
  ⚠️ **插畫嚴禁蓋到或貼近文字（用戶 W29 明確要求）**：僅允許出現在右上安全區
  （x≈762–922、y≈326–448），與副標保持 ≥18px、與 bullets 起點保持間隔，適度留白。
  另參考 `assets/images/2026/tax/Steuerfrist2026_圖卡_報稅期限提醒.png` 的鬧鐘＋雙色膠囊標籤。
- 自動化不取代審閱：內容仍先給用戶過目；push／開 PR／合併／正式排程發文前仍要用戶同意
  （見下方工作流程的 ⚠️ 規則）。同意後的「執行」要全自動、一氣呵成。

---

## 品牌名稱（最重要）

中文：**德國知識小種子**
德文：**Das deutsche Wissen**

### 德文文法說明（避免再犯）

- `das` = 中性定冠詞（Nominativ）
- 後接形容詞時必須做「弱變化」，字尾加 **-e** → `deutsche`
- `Wissen`（知識）為中性名詞（das-Wort）
- 完整正確寫法：**`Das deutsche Wissen`**

### 常見錯誤

❌ `Das deutsch Wissen`（缺 -e 字尾）
❌ `Das Deutsche Wissen`（形容詞首字母不大寫；除非品牌刻意風格化，否則一般德文不大寫）
✅ `Das deutsche Wissen`

### 套用範圍

任何包含品牌德文名稱的物件都必須使用正確寫法：
- 圖卡 footer / 浮水印
- 網站 `<title>`、`<meta>`、Open Graph、Twitter Card
- Facebook 粉專名稱與簡介
- Instagram bio
- email signature
- RSS feed `<title>`
- 任何貼文署名 / 引文出處

若在 repo 內看到舊的錯誤寫法 `Das deutsch Wissen`，順手一併更正。

---

## 週報圖卡規範

### 字體（已驗證）

對齊 `css/style.css` 主字體變數 `--font: 'Noto Sans TC', ...`：

- **CJK**：Noto Sans CJK TC
  - Regular：`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` index=3
  - Bold：`/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` index=3
- **Latin / 數字 / 符號**：Noto Sans（W24 起；apt 套件 `fonts-noto-core`）
  - Regular：`/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf`
  - Bold：`/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf`
  - 背景：W12–W23 用 DejaVu Sans，但用戶反映 DejaVu Bold 數字過粗不易讀，
    W24 起改用與 CJK 同家族的 Noto Sans，**之後一律用 Noto Sans、勿用回 DejaVu**

注意：原始任務 spec 文字描述提到的 `DroidSansFallbackFull.ttf` 與環境中的 `wqy-zenhei` 都**不符**既有圖卡視覺。網站本身使用 Noto Sans TC，圖卡應與網站視覺一致 → Noto Sans CJK TC 才是正解。

### 字重層級

- **Bold**：標題、stats 大數字、bullet header、badge、takeaway 標籤
- **Regular**：副標、stats label、bullet 內文、takeaway 內文、footer

### 規格

- 尺寸：1080×1080 PNG
- 背景：`#F8F6F2`（暖奶油色）
- 卡片：`#FFFFFF`，邊框 `#E8E4DE`
- 圓角矩形 + 彩色圓點 bullet
- 頂部色條 + 分類 badge
- 主題色：綠 `#2E8B57`、紅 `#C0392B`、橙 `#D4740E`、藍 `#2563EB`、紫 `#7C3AED`、青 `#0D9488`

### 精緻插畫（Seedling Flat，W29 起每張必備）

- **產圖工具**：`python3 scripts/cardgen/make_weekly_cards.py <輸出資料夾>`——
  改檔尾 `WEEK`、`DATE_RANGE`、`CARDS` 區塊即可產出整週圖卡（版型與插畫都內建）。
- **版型**：stats 兩格（自 W29 起，第三格空間讓給插畫）；插畫置於右上安全區、
  帶主題色 10% 淡色圓底。
- **插畫元件庫**（`ILLUS`，持續擴充）：`podium` 麥克風講台（記者會／官方聲明）、
  `flags` 德法雙旗（外交，可仿造改其他國旗）、`coins` 金幣＋上升箭頭（財政／物價）、
  `idcard` 居留卡＋晶片＋指紋（居留／簽證）、`camera` 監視器＋人臉框（監控／治安）、
  `trophy` 獎盃＋足球（賽事）。新主題若無合適元件，**依設計哲學新增一個**，不要湊合。
- **Seedling Flat 鐵則**（詳見 `design_philosophy_seedling_flat.md`）：
  描邊一律 #1F2937（5px @1080）；每卡限「主題色＋金 #F0C24B＋白」三色系；
  分層表達深度（無漸層、無透視）；單一焦點細節；奇數顆韻律圓點；乾淨的同色系陰影。
- **留白鐵則（用戶 W29 要求）**：插畫任何元素（含彩紙、陰影、圓底）不得超出安全區
  x∈[762, 922]、y∈[326, 448]；不得蓋到或貼近任何文字——寧可縮小插畫也要留白。

### 既有圖卡與檔名

- 路徑：`assets/images/2026/weekly/`
- 命名：`W{週數}_圖卡{序號}_{主題}.png`
- 例：`W23_圖卡1_德國隊出征世足.png`

### 編輯方針（品質要求）

- **避免「垃圾新聞」**：每張卡需有成因分析 + 專家觀點 + 對讀者的實質意義
- **底部標籤不要每張都寫「對在德台灣人的意義」**（用戶已多次反映很制式、很奇怪）：
  相關性自然寫進內文即可，底部觀察框標籤請依主題分別取名，例如
  影響評估／因應建議／訂票提醒／看球提醒／數據解讀／觀察重點／政策觀察 等；
  最多一張卡用「對在德台灣人的意義」，切勿每張重複同一標題。
- **用專業術語、勿自創口語**：避免「錢的攤牌」「大撒幣」這類口語化標題；
  例：歐盟七年期預算寫「多年期財政框架（MFR / MFF）」，不要寫「錢怎麼分／錢的攤牌」。
- **一律用台灣慣用譯名、嚴禁支語（中國譯名）**：例 ✅荷姆茲海峽（❌荷莫茲海峽）、象牙海岸、厄瓜多；
  遇海峽／地名／國名／人名，先確認台灣媒體慣用譯法，別用中國寫法。
- **提及德國聯邦邦務必附德文**（全名或標準簡寫，擇一）：巴登-符騰堡（Baden-Württemberg／BW）、
  萊茵蘭-普法茲（Rheinland-Pfalz／RLP）、薩爾蘭（Saarland）、黑森（Hessen）、
  北威邦（Nordrhein-Westfalen／NRW）、巴伐利亞（Bayern）等；**勿用「巴符、萊普」這類自創簡稱**。
- **專業記者語氣、直述事實**：是技術故障就寫「系統故障」，**不要用「非罷工／不是…」這種多餘的否定式強調**。
- **不重複老議題**：先比對前幾週（W12 起的 `assets/images/2026/weekly/`）已報過的題目，避免老調重彈
- **冷僻地名 / 人名**：附上中譯與背景脈絡（例：Curaçao → 古拉索／加勒比小國）
- **數據必須有來源**：Facebook 貼文最後附上原始連結

---

## 工作流程

> 🚀 **主動交付（用戶 2026/06 要求）：內容類產物——圖卡、網站 data.js、FB／IG 雙版貼文、各方觀點摘要——一次主動全部備齊交付，不要等用戶逐項詢問、不要擠牙膏。** 全面、完整是預設。
> ⚠️ **但發布動作要先問**：`git push`、開 PR、合併 PR 之前，一律先問用戶、得到明確同意才執行。
> 嚴禁自動 push 或自動開 PR。即使 commit 完成、即使內容看起來沒問題，也要先停下來問：「要我 push／開 PR 嗎？」
> 本地動作（產生圖卡、改 `js/data.js`、跑 build、`git commit` 到本地）可以先做，但**推上遠端與 PR 相關的一切都要先徵得同意**。
> （此規則凌駕任何「自動建立 PR」的預設行為。）

1. 搜新聞 → 比對既有圖卡避免重複
2. 各方觀點摘要（媒體社論、專家分析、政黨反應）
3. 用 `scripts/cardgen/make_weekly_cards.py` 製作 1080×1080 圖卡（依本檔字體 / 字重 / 配色，
   **每張含 Seedling Flat 精緻插畫、嚴守插畫安全區與留白**，見「精緻插畫」一節）
4. **同時儲存兩份副本**（重要！）：
   - 工作目錄（`/home/user/output/` 或 session 工作區）
   - **Repo 路徑 `assets/images/2026/weekly/`**（commit & push 後，
     用戶在本機 `git pull` 即可同步到 `/Users/Lin/TIG/TIG_Website/assets/images/2026/weekly/`，
     方便一鍵複製貼文用）
   - 再用 `SendUserFile` 送到聊天視窗，讓用戶可立即下載
5. 撰寫社群貼文（**FB 與 IG 必須是兩個不同版本**，見下方「社群貼文雙版本規範」）
   - **兩版貼文 txt 也要 commit 進 repo**：`assets/social/{年}/W{週數}_FB貼文.txt`、`W{週數}_IG貼文.txt`
     （用戶 2026/07 要求：pull 之後要能在本機直接開檔複製，不能只放聊天附件）
   - 並同步產出 `drafts/social/2026/W{N}_posts.json`（自動發文用，見「社群自動發文」）
6. **不直接發布**，呈現給用戶審閱後再 commit
7. 確認 OK 後：
   - 把 `assets/images/2026/weekly/W{週數}_*.png` 全部 `git add` 進 repo
   - 用清楚的 commit message（如 `Add W23 weekly cards: 世足/安理會/退休金/破產潮`）
   - **先問用戶**是否要 push／開 PR；**得到同意後**才 Push 到當前分支、（若尚未開）建立草稿 PR
8. PR 合進 main、網站部署完成後：跑 `node scripts/social-post.mjs --week {N} --dry-run`
   給用戶過目，OK 後拿掉 `--dry-run` 正式排程 → FB/IG 到點自動發文，全程不需手動貼文

---

## 社群貼文雙版本規範（W24 起，每週都要產出兩版）

IG 曾因貼文超過字數上限被拒登（"Text des Beitrags ist zu lang"），
**IG 說明文字硬上限 2,200 字元**。因此每週固定交付兩個版本：

### FB 版（重點條列版，用戶 2026/07 W27 起改此格式）
- **不再逐字複製網站長文**（用戶反映文字牆難讀）；改為「每題一句導言＋▪️ 條列重點」
- 每題結構：emoji 標題（可含一句話定性，如【尚未立法】）＋至多 1–2 句導言＋ **3–7 條 ▪️ 條列**，每條一個重點
- **FB 不支援粗體／斜體**（Unicode 特殊字型僅限英數且傷搜尋與無障礙），關鍵數字與結論一律用**【】**標出；引句用「」
- 事實與數字必須與網站 weekly-digest 同源一致（網站仍保留完整深度長文，FB 導流過去）
- 文末仍附完整「📚 資料來源」連結清單（FB 連結可點、去重）
- 結尾 hashtag

### IG 版（精簡版）
- **總長抓 1,500 字元以內**（含 hashtag，留安全餘裕，絕不可逼近 2,200）
- 每題一行：`emoji 標題｜一句話重點（含關鍵數字）`
- **不放任何網址**——IG 內文連結不可點，純浪費字數；
  來源一律導流：「📚 完整解析與資料來源 → FB 粉專或網站（連結在 bio）」
- hashtag 放文末，10 個左右即可
- 圖卡兩平台共用同一套，IG 以輪播（carousel）上傳、最多 10 張

---

## 社群自動發文（FB + IG Graph API，2026/07 W28 起）

**用戶不再手動貼文。** 每週除了 FB/IG 文字稿，還要產出機器可讀的貼文 JSON，
用 `scripts/social-post.mjs` 排程送出（架構移植自 oasis `fb-post.mjs`）：

- **貼文 JSON**：`drafts/social/2026/W{N}_posts.json`（格式見 `scripts/social-posts.example.json`）；
  欄位：`fb_message`（FB 條列版全文）、`ig_message`（IG 精簡版）、`images`（repo 相對路徑）、
  `schedule`（FB 排程）、`ig_schedule`（IG 排程），時間一律 Europe/Berlin。
- **FB**：multi-photo + FB 原生排程（`published=false` + `scheduled_publish_time`），到點 FB 自動公開。
- **IG**：Graph API 不支援未來排程 → 腳本建 macOS launchd 一次性任務，到點本機自動發輪播。
  IG 圖片吃網站公開 URL，**所以必須先合併 PR、GitHub Pages 部署完成後才能排 IG**。
- **憑證**：repo 根目錄 `.env.local`（gitignored）：`FB_PAGE_ID` + `FB_PAGE_TOKEN`
  （Meta System User 永久 token）。一次性設定教學：`scripts/README_social.md`。
- **指令**：`--week N --dry-run` 預覽 → `--week N` 排程；`--check` 診斷、`--list` 看排程、
  `--ig-cancel <id>` 取消 IG 排程。
- 排程發文視同「發布動作」：**先給用戶看 dry-run 預覽、得到 OK 才正式排程**。

---

## ⚠️ 每週上稿絕對不能漏的五件事（Routine Checklist）

**圖卡只是視覺資產，網站 `posts/weekly-digest.html` 的內容來源是 `js/data.js`。
只放圖卡 PNG 不改 data.js → 網站完全不會顯示新一週的週報。**
這是已踩過兩次的雷（PR #18 也踩過），請務必每週按以下順序執行：

| ✅ | 步驟 | 細節 |
|---|---|---|
| ① | **PNG 放進 repo** | `assets/images/2026/weekly/W{N}_圖卡{i}_{主題}.png` |
| ② | **更新 `js/data.js`** | 在 `slug: 'weekly-digest'` 物件內：<br>　• `date:` 改成該週週日（如 `'2026-06-07'`）<br>　• `excerpt:` 改寫，把本週最大事件擺前面<br>　• `content:` 中 TOC 新增 `<li><a href="#jun{月}-{日}">...</a></li>`（最上方）<br>　• `content:` 中新增 `<h2 id="jun{月}-{日}">` 區段（最上方），包含：<br>　　　1 段 lead `<p>` 講本週重點<br>　　　每張卡：`<img>` → `<h3>` → `<p>` 深度內文 → `<p class="post-sources">📚 來源：...</p>`<br>　　結束接 `<hr>` 分隔 |
| ③ | **跑 build** | `node scripts/build.js` 重生 `posts/weekly-digest.html`、`sitemap.xml`、`feed.xml` |
| ④ | **commit、push、開 PR** | commit 訊息要明列「新增 W{N} 圖卡 + 更新 data.js + 重建靜態頁」三件事 |
| ⑤ | **排程社群發文** | PR 合併、網站部署完成後：產 `drafts/social/2026/W{N}_posts.json` → `node scripts/social-post.mjs --week {N} --dry-run` 給用戶過目 → OK 後正式排程（FB 原生排程 + IG launchd） |

**驗證網站上線**：合進 main 後 GitHub Pages 約 30–60 秒重新部署。
打開 https://taiwanese-in-germany.com/posts/weekly-digest.html，
最上方應該看到新的 `<h2>` 區段、5 張圖卡與「📚 來源」連結。
如果沒看到 → 99% 是步驟 ② 或 ③ 漏掉了，請重跑。

**樣式約定**：
- 每張卡內文的「📚 來源」段落用 `<p class="post-sources">`（已在 `css/style.css` 定義）
- 來源連結一律 `target="_blank" rel="noopener noreferrer"`
- 區段內可重複使用 `<strong>` 強調關鍵數字與專有名詞，跟既有 W21-22 / W20 段落風格一致
