# social/ — 社群貼文文字稿與排程檔（找檔案先看這裡）

**一個主題一個資料夾，不分年份。** 每篇貼文固定兩個檔：

- `{名稱}_社群貼文.txt` — 人看的：FB 條列版＋IG 精簡版，開頭註明用哪些圖卡、建議排程時間
- `{名稱}_posts.json` — 機器用的：`node scripts/social-post.mjs` 自動排程發文吃這個檔

## 資料夾分類

| 資料夾 | 內容 | 對應圖卡位置 |
|---|---|---|
| `weekly/` | 德國週報（W27、W28、W29…） | `assets/images/2026/weekly/` |
| `tax/` | 報稅系列（期限提醒 Steuerfrist、申報義務 Steuerpflicht…） | `assets/images/2026/tax/` |
| `bbva/` | BBVA 銀行推薦／開箱／信用卡 | `assets/images/bbva/` |
| `worldcup/` | 世足特別版 | `assets/images/2026/weekly/`（世足卡混在週報卡中） |
| `visa/` | Visa Bonus 回饋活動（海外刷卡 2%、秋季網購檔） | `assets/images/2026/visa/` |

新主題 → 開新資料夾（小寫英文短名），並在上表加一列。

## 為什麼圖卡不搬過來？

`assets/images/**` 的路徑就是網站的公開網址（文章頁 `<img>`、sitemap、
已發布的社群貼文都指向它），搬動會讓網站圖片 404，所以圖卡留在原位、
年份層也保留。要找某篇貼文的圖卡：開該貼文的 `_社群貼文.txt`，
**第一段就列了圖卡完整路徑**；或按上表直接進對應資料夾。

## 排程指令備忘

```bash
node scripts/social-post.mjs --week 29 --dry-run          # 週報：預覽
node scripts/social-post.mjs --week 29                    # 週報：正式排程
node scripts/social-post.mjs --file social/tax/Steuerpflicht_posts.json --dry-run   # 單篇主題
node scripts/social-post.mjs --list                       # 看目前排程
```

IG launchd 的執行紀錄在 `social/ig-post.log`（gitignored）。
其餘檔案（txt、json、本 README）**都要 commit 進 repo**，pull 之後才能直接開檔複製。
