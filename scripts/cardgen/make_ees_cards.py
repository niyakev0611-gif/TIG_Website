# -*- coding: utf-8 -*-
"""入境歐洲新制（EES／EasyPASS／ETIAS）— 主題圖卡產生器
================================================================
產出 4 張 Seedling Flat 資訊卡（熱門度由高到低）：
  1. 三種身分對照（持德國居留／台灣護照短期來訪／有德國籍）
  2. EES：第一次入境要按指紋、拍臉（2026/4/10 全面上路）
  3. EasyPASS：持居留卡直接走自動通關；台灣護照短期停留走 RTP 登記
  4. ETIAS：延期、現在還不用申請，小心假網站

用法：
  python3 scripts/cardgen/make_ees_cards.py <輸出資料夾>
"""
import os
import sys

from make_weekly_cards import make_card, check_glyphs

LABEL = '出入境'
DATE_RANGE = '2026/10'  # footer 中段上限約 400px

CARDS = [
 dict(
  theme='#2563EB', badges=[('出入境新制', True), ('身分對照', False)], illu='idcard',
  title='入境歐洲新制，你要做什麼？',
  subtitle='EES、EasyPASS、ETIAS 三個新名詞，要做的事依身分而不同',
  stats=[('不用登記', '持德國居留卡的人'),
         ('要登記', '台灣護照短期來訪')],
  bullets=[
   ('持德國居留卡', 'EES 不用登記、ETIAS 不用申請；12 歲以上可以直接走 EasyPASS 自動通關。'),
   ('台灣親友短期來訪', '第一次入境要按指紋、拍臉部影像；ETIAS 還沒上路，現在不用申請。'),
   ('有德國籍', '用德國護照或身分證入出境，EES 與 ETIAS 都不適用。'),
  ],
  takeaway=('出門提醒', '居留卡要跟護照一起帶；邊境人員看到居留卡，才能確認你不必登記 EES。'),
  file='EES_圖卡1_三種身分.png'),
 dict(
  theme='#0D9488', badges=[('EES', True), ('2026/4/10 全面上路', False)], illu='fingerscan',
  title='第一次入境，要按指紋、拍臉',
  subtitle='歐盟出入境系統 EES 取代護照蓋章，自動計算 90 天停留期限',
  stats=[('12 歲', '起要按指紋'),
         ('3 年', '登記資料保存期限')],
  bullets=[
   ('登記一次就好', '在第一個入境的申根國家登記護照資料、臉部影像與指紋，之後入出境只要比對。'),
   ('轉機要預留時間', '經其他申根國轉機，就在轉機那一國登記；12 歲以下兒童只拍臉部影像。'),
   ('尖峰時段要排隊', '依《金融時報》分析，今年 7 月法蘭克福機場平均要等 120 分鐘，是去年同期的兩倍。'),
  ],
  takeaway=('因應建議', '親友來訪前提醒多留通關時間；拒絕提供指紋或臉部影像，會被拒絕入境。'),
  file='EES_圖卡2_指紋登記.png'),
 dict(
  theme='#2E8B57', badges=[('EasyPASS', True), ('自動通關', False)], illu='egate',
  title='持居留卡，直接走自動通關',
  subtitle='德國 8 座機場設有 EasyPASS 閘門：放上護照、看鏡頭就能通關',
  stats=[('12 歲', '以上可以使用'),
         ('0 €', '登記與使用都免費')],
  bullets=[
   ('持德國居留卡', '不用事先登記，帶電子護照與居留卡直接使用；只持長期簽證（D 簽）的人限出境使用。'),
   ('台灣護照短期停留', '先到機場的聯邦警察服務處登記 EasyPASS-RTP，多半不用預約，效期跟著護照。'),
   ('有閘門的機場', '柏林、杜塞道夫、法蘭克福、漢堡、漢諾威、科隆／波昂、慕尼黑、斯圖加特。'),
  ],
  takeaway=('使用提醒', '過閘門前先取下帽子與太陽眼鏡；換了新護照，RTP 要重新登記。'),
  file='EES_圖卡3_自動通關.png'),
 dict(
  theme='#D4740E', badges=[('ETIAS', True), ('延期', False)], illu='webpermit',
  title='ETIAS 延期，現在還不用申請',
  subtitle='原訂 2026 年底上路，官方已撤下日期；外媒報導最快 2027 年',
  stats=[('20 €', '規費（18–70 歲）'),
         ('3 年', '核准後的效期')],
  bullets=[
   ('不是簽證', '台灣護照免簽待遇不變；ETIAS 是出發前上網填寫的旅行許可，上路後短期入境才需要。'),
   ('持居留卡不用', '持德國或其他申根國居留卡的人不用申請，有歐盟國籍也不用。'),
   ('小心假網站', '歐盟邊境管理局 Frontex 已發現上百個非官方網站；官方入口只在 europa.eu 網域。'),
  ],
  takeaway=('防詐提醒', 'ETIAS 目前不受理任何申請：現在要你付錢申請的網站，都不是官方網站。'),
  file='EES_圖卡4_ETIAS延期.png'),
]

if __name__ == '__main__':
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        check_glyphs(c)
        make_card(c, os.path.join(OUT, c['file']), LABEL, DATE_RANGE)
        print('✓', c['file'])
