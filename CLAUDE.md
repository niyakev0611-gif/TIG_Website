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
- **Latin / 數字 / 符號**：DejaVu Sans
  - Regular：`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
  - Bold：`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`

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
4. 撰寫 FB 繁中貼文 + 來源連結
5. **不直接發布**，呈現給用戶審閱後再 commit
