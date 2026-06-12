# CLAUDE.md — 德國知識小種子 Das deutsche Wissen

本檔為 Claude Code 在此 repo 工作時的長期記憶與品牌守則。每個 session 開啟時都會自動讀取。

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

### 既有圖卡與檔名

- 路徑：`assets/images/2026/weekly/`
- 命名：`W{週數}_圖卡{序號}_{主題}.png`
- 例：`W23_圖卡1_德國隊出征世足.png`

### 編輯方針（品質要求）

- **避免「垃圾新聞」**：每張卡需有成因分析 + 專家觀點 + 對在德台灣人的意義
- **不重複老議題**：先比對前幾週（W12 起的 `assets/images/2026/weekly/`）已報過的題目，避免老調重彈
- **冷僻地名 / 人名**：附上中譯與背景脈絡（例：Curaçao → 古拉索／加勒比小國）
- **數據必須有來源**：Facebook 貼文最後附上原始連結

---

## 工作流程

1. 搜新聞 → 比對既有圖卡避免重複
2. 各方觀點摘要（媒體社論、專家分析、政黨反應）
3. Python Pillow 製作 1080×1080 圖卡（依本檔字體 / 字重 / 配色）
4. **同時儲存兩份副本**（重要！）：
   - 工作目錄（`/home/user/output/` 或 session 工作區）
   - **Repo 路徑 `assets/images/2026/weekly/`**（commit & push 後，
     用戶在本機 `git pull` 即可同步到 `/Users/Lin/TIG/TIG_Website/assets/images/2026/weekly/`，
     方便一鍵複製貼文用）
   - 再用 `SendUserFile` 送到聊天視窗，讓用戶可立即下載
5. 撰寫 FB 繁中貼文 + 來源連結
6. **不直接發布**，呈現給用戶審閱後再 commit
7. 確認 OK 後：
   - 把 `assets/images/2026/weekly/W{週數}_*.png` 全部 `git add` 進 repo
   - 用清楚的 commit message（如 `Add W23 weekly cards: 世足/安理會/退休金/破產潮`）
   - Push 到當前分支並（若尚未開）建立草稿 PR

---

## ⚠️ 每週上稿絕對不能漏的四件事（Routine Checklist）

**圖卡只是視覺資產，網站 `posts/weekly-digest.html` 的內容來源是 `js/data.js`。
只放圖卡 PNG 不改 data.js → 網站完全不會顯示新一週的週報。**
這是已踩過兩次的雷（PR #18 也踩過），請務必每週按以下順序執行：

| ✅ | 步驟 | 細節 |
|---|---|---|
| ① | **PNG 放進 repo** | `assets/images/2026/weekly/W{N}_圖卡{i}_{主題}.png` |
| ② | **更新 `js/data.js`** | 在 `slug: 'weekly-digest'` 物件內：<br>　• `date:` 改成該週週日（如 `'2026-06-07'`）<br>　• `excerpt:` 改寫，把本週最大事件擺前面<br>　• `content:` 中 TOC 新增 `<li><a href="#jun{月}-{日}">...</a></li>`（最上方）<br>　• `content:` 中新增 `<h2 id="jun{月}-{日}">` 區段（最上方），包含：<br>　　　1 段 lead `<p>` 講本週重點<br>　　　每張卡：`<img>` → `<h3>` → `<p>` 深度內文 → `<p class="post-sources">📚 來源：...</p>`<br>　　結束接 `<hr>` 分隔 |
| ③ | **跑 build** | `node scripts/build.js` 重生 `posts/weekly-digest.html`、`sitemap.xml`、`feed.xml` |
| ④ | **commit、push、開 PR** | commit 訊息要明列「新增 W{N} 圖卡 + 更新 data.js + 重建靜態頁」三件事 |

**驗證網站上線**：合進 main 後 GitHub Pages 約 30–60 秒重新部署。
打開 https://taiwanese-in-germany.com/posts/weekly-digest.html，
最上方應該看到新的 `<h2>` 區段、5 張圖卡與「📚 來源」連結。
如果沒看到 → 99% 是步驟 ② 或 ③ 漏掉了，請重跑。

**樣式約定**：
- 每張卡內文的「📚 來源」段落用 `<p class="post-sources">`（已在 `css/style.css` 定義）
- 來源連結一律 `target="_blank" rel="noopener noreferrer"`
- 區段內可重複使用 `<strong>` 強調關鍵數字與專有名詞，跟既有 W21-22 / W20 段落風格一致
