# -*- coding: utf-8 -*-
"""THG-Quote 電動車碳權 — 主題圖卡產生器
================================================================
產出三張 Seedling Flat 資訊卡（制度總覽／資格檢查／選商指南）。
排序依熱門度：能領多少錢 → 我能不能領 → 怎麼選業者。

用法：
  python3 make_thg_cards.py <輸出資料夾>
"""
import os
import sys

from make_weekly_cards import make_card

LABEL = 'THG-Quote'
DATE_RANGE = '2026'

CARDS = [
 dict(
  theme='#2E8B57', badges=[('省錢攻略', True), ('每年可領', False)], illu='evcharge',
  title='電動車每年白領 300–430 €',
  subtitle='THG-Quote 溫室氣體減量配額｜上傳行照就能申請的法定制度',
  stats=[('300–430 €', '2026 年純電小客車行情'),
         ('11/15', '每年申請截止日')],
  bullets=[
   ('這筆錢從哪來', '法律要求石油業者逐年降低燃料碳排（2026 年約 12.1%），減不動就得向外買配額——你的電動車正好有配額可賣。'),
   ('你只要做一件事', '行照（Zulassungsbescheinigung Teil I）拍照上傳，其餘由業者代送聯邦環境署認證並賣出；不必回報里程或電費單。'),
   ('多久領一次', '每車每年一次、必須重新申請，不會自動續約。選「立即撥款」幾個工作天入帳，走市場價的約等半年。'),
  ],
  takeaway=('申請提醒', '聯邦環境署收件到 11 月 15 日，業者還需作業時間——10 月底前送出最保險，今年還沒辦的現在就動手。'),
  file='THGQuote2026_圖卡1_電動車碳權.png'),
 dict(
  theme='#2563EB', badges=[('資格檢查', True), ('注意排除', False)], illu='checklist',
  title='誰能領？認的是行照上的車主',
  subtitle='純電才行、插電式混合不行；租賃車只要行照寫你就算你的',
  stats=[('BEV', '限純電動車'),
         ('1 次', '每車每年限領一次')],
  bullets=[
   ('可以領的人', '行照 Teil I 上登記的車主（Halter）本人。租賃車只要行照寫的是你就算你的；登記在公司名下則歸公司。'),
   ('可以領的車', '純電動小客車、電動機車與速可達（L 類、時速逾 45 公里）、電動商用車、電動巴士與公共充電樁營運者。'),
   ('直接出局的', '插電式混合動力（PHEV）不符資格，制度只認純電；免掛牌的電動滑板車、電動自行車也不能申請。'),
  ],
  takeaway=('稅務提醒', '私人車主領到的獎金免稅、不必寫進報稅單；車若登記在公司或自營業者名下，則要計入營業收入。'),
  file='THGQuote2026_圖卡2_誰能領.png'),
 dict(
  theme='#D4740E', badges=[('選商指南', True), ('合約地雷', False)], illu='contract',
  title='保證金額，還是賭市場價？',
  subtitle='配額價格會波動；簽約前先看清楚「讓與期間」',
  stats=[('300 €', '保證方案常見金額'),
         ('2 年', '部分合約的讓與期間')],
  bullets=[
   ('兩種方案的差別', '保證金額（Garantieprämie）先講好多少就是多少；浮動方案（Flexprämie）隨行情走，可能多賺也可能少領。'),
   ('價格真的會震盪', '2022 年一度上看 400 €，2024 年秋天跌破 100 €；2026 年因法定比例調高，行情回到 300 € 上下。'),
   ('簽約前先看這一行', '讓與期間（Abtretungszeitraum）——有些合約一次綁兩年，等於明年不能改投出價更高的業者。'),
  ],
  takeaway=('比價建議', '配額一年一約：每年重新申請時順手比一次價（ADAC、Verivox、Finanztip 都有年度比較），哪家出價高就領哪家。'),
  file='THGQuote2026_圖卡3_選商指南.png'),
]

if __name__ == '__main__':
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        make_card(c, os.path.join(OUT, c['file']), LABEL, DATE_RANGE)
