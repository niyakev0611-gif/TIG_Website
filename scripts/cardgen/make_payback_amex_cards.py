# -*- coding: utf-8 -*-
"""PAYBACK American Express 卡 — 主題圖卡產生器
================================================================
產出：
  1-5. Seedling Flat 資訊卡（推薦加碼／集點方式／點數價值／誰適合／領獎條件）
  6.   官方推薦頁截圖框卡（4.000 點的證據；--shots 指定截圖資料夾）

用法：
  python3 scripts/cardgen/make_payback_amex_cards.py <輸出資料夾> [--shots <截圖資料夾>]
"""
import os
import sys

from make_weekly_cards import make_card, make_table_card, check_glyphs
from make_visa_bonus_cards import make_shot_card
import make_visa_bonus_cards as vb

LABEL = 'PAYBACK Amex'
DATE_RANGE = '9/27 止'  # footer 中段上限約 400px（量測：品牌字起點 x=716）

CARDS = [
 dict(
  theme='#2563EB', badges=[('省錢情報', True), ('9/27 截止', False)], illu='bankcard',
  title='PAYBACK Amex 加碼：雙方各 40 €',
  subtitle='推薦活動加碼到 2026/9/27：你我各拿 4.000 點，卡片本身終身免年費',
  stats=[('4.000 點', '＝ 40 €，原本只有 1.000'),
         ('0 €', '年費，附卡也免費')],
  bullets=[
   ('加碼多少', '透過推薦連結申辦，被推薦人與推薦人各得 4.000 PAYBACK 點；平常這個數字是 1.000 點。'),
   ('點數等於現金', 'PAYBACK 1 點 ＝ 1 分歐元，4.000 點就是 40 €，可折抵消費、匯到帳戶，或 1:1 換成里程。'),
   ('活動到 9 月 27 日', '官方頁面掛著「Aktion bis 27.09.2026」的黃標，過了就回到 1.000 點。'),
  ],
  takeaway=('版主查證', '版主用自己的推薦連結、在未登入狀態實測，頁面確實顯示 1.000 劃掉改成 4.000 點。'),
  file='PaybackAmex_圖卡1_雙方各四千點.png'),
 dict(
  theme='#2E8B57', badges=[('怎麼集點', True), ('每 3 € 1 點', False)], illu='coins',
  title='這張卡怎麼幫你集點',
  subtitle='刷卡集卡片的點，出示 PAYBACK 條碼再集商家的點',
  stats=[('1 點 / 3 €', '刷卡到哪都算'),
         ('0.33%', '單看刷卡的回饋率')],
  bullets=[
   ('刷卡就有點', '不限商家、不限國內外，每 3 € 消費得 1 點——但加油站的消費明文不計點。'),
   ('在合作商家雙重集點', 'EDEKA、dm、Aral、Amazon 等 PAYBACK 夥伴：出示條碼集商家點，再用這張卡付款集卡片點。'),
   ('點數不會過期', '只要你還在 PAYBACK 計畫裡，點數就有效；連續三年沒集點才會依 PAYBACK 條款失效。'),
  ],
  takeaway=('10/13 有變動', 'PAYBACK MAX 改制為 Amex PLUS：年費 35 €、年消費 20,000 € 以內集點翻倍——要年花 10,500 € 以上才划算。'),
  file='PaybackAmex_圖卡2_怎麼集點.png'),
 dict(
  kind='table',
  theme='#C0392B', badges=[('方案比較', True), ('10/13 改制', False)],
  title='免費版、MAX 與 PLUS 差在哪',
  subtitle='卡只有一張，MAX 與 PLUS 是加在上面的付費方案，10/13 起換手',
  tables=[
   dict(caption='三個方案怎麼分',
        cols=['項目', '免費版', 'MAX（終止）', 'PLUS（新）'],
        widths=[0.22, 0.24, 0.27, 0.27],
        rows=[
         ['年費', ('0 €', True), '35 €', '35 €'],
         ['集點率', '每 3 € 1 點', '每 3 € 2 點', '每 3 € 2 點'],
         ['翻倍上限', '—', ('無上限', True), ('年 20,000 €', True)],
         ['額外權益', '—', '無', '月加碼＋券包'],
         ['誰能用', '所有人', '僅既有客戶', '所有人'],
        ]),
   dict(caption='升級 PLUS 划算嗎？（點數價值扣掉 35 € 年費）',
        cols=['一年刷卡', '免費版', 'PLUS', '差額'],
        widths=[0.26, 0.24, 0.24, 0.26],
        rows=[
         ['6,000 €', '20.0 €', '5.0 €', ('-15.0 €', True)],
         ['10,500 €', '35.0 €', '35.0 €', ('打平點', True)],
         ['20,000 €', '66.7 €', '98.3 €', '+31.7 €'],
         ['50,000 €', '166.7 €', '198.3 €', '+31.7 €'],
        ]),
  ],
  note=('關鍵一句', '翻倍在 20,000 € 封頂，年刷不到 10,500 € 就維持免費版。'),
  file='PaybackAmex_圖卡3_MAX與PLUS差異.png'),
 dict(
  theme='#0D9488', badges=[('點數換算', True), ('值多少錢', False)], illu='piggybank',
  title='PAYBACK 點到底值多少',
  subtitle='1 點 ＝ 1 分歐元，換里程有機會更值錢',
  stats=[('1 點 = 1 分', '折抵或匯入帳戶'),
         ('1 : 1', '可換 Miles & More 里程')],
  bullets=[
   ('三種用法', '在合作商家直接折抵、兌換獎品目錄的商品，或申請把點數匯進自己的德國帳戶——匯率都是 100 點 1 €。'),
   ('換里程可能更划算', 'PAYBACK 點可 1:1 轉成 Lufthansa Miles & More 里程；里程的實際價值常高於 1 分，看你怎麼兌。'),
   ('別高估日常回饋', '單看刷卡是 0.33%，在合作商家加上商家點大約 0.8%——這張卡真正的甜頭是開卡的 40 €。'),
  ],
  takeaway=('數據解讀', '把 4.000 點當成一次性的 40 €，之後的點數當零頭：想要高回饋率的人，這張不是主力卡。'),
  file='PaybackAmex_圖卡4_點數值多少.png'),
 dict(
  theme='#7C3AED', badges=[('買前確認', True), ('誰適合', False)], illu='checklist',
  title='誰適合辦、誰別浪費時間',
  subtitle='Amex 在德國約八成五商家能刷，小店與麵包店常常不收',
  stats=[('約 85%', '德國 Amex 接受度'),
         ('每月全額', 'Charge Card 自動扣款')],
  bullets=[
   ('適合這些人', '本來就在集 PAYBACK、常逛 EDEKA 與 dm、想無痛拿 40 €，而且手上已有 Visa 或 Mastercard 當備援。'),
   ('這些人跳過', '討厭多一張卡要管、常在小店與市場消費、或不想被 SCHUFA 多查一次的人。'),
   ('它是簽帳卡不是信用卡', '每月帳單全額自動扣款、不能分期；好處是不會滾利息，但戶頭要留足餘額。'),
  ],
  takeaway=('實用提醒', '出門別只帶 Amex：獨立餐廳、麵包店、小攤子常因手續費較高而不收，身上要有第二張卡。'),
  file='PaybackAmex_圖卡5_誰適合辦.png'),
 dict(
  theme='#D4740E', badges=[('注意事項', True), ('別白做工', False)], illu='contract',
  title='想拿到 4.000 點，五個條件',
  subtitle='少一個都可能讓點數飛掉，申辦前先逐條對過',
  stats=[('18 個月', '新客戶認定期間'),
         ('4–6 週', '點數入帳時間')],
  bullets=[
   ('必須算新客戶', '申請前 18 個月內不能是同一款 Amex 卡的主卡持有人——不論當初為什麼解約都算。'),
   ('要從推薦連結進去', '直接到官網申辦只會拿到一般的 1.000 點；點數在成功發卡後 4 到 6 週入帳。'),
   ('一年內別解約', '發卡後 12 個月內解約或換卡，點數資格會被追溯取消；另外還要通過 SCHUFA 與收入審核。'),
  ],
  takeaway=('保險做法', '官方頁面說是「首次刷卡」後給點、腳註寫「成功發卡後」——拿到卡就先刷一筆，兩種說法都滿足。'),
  file='PaybackAmex_圖卡6_五個條件.png'),
]

SHOT_CARDS = [
 dict(src='crop_offer.png', theme='#2563EB', badge='官方頁面實測',
      title='未登入也看得到：4.000 點',
      caption='用推薦連結打開的畫面：1.000 劃掉改成 4.000 PAYBACK 點，黃標寫著 Aktion bis 27.09.2026，下方列出終身免年費、每 3 € 1 點、附卡免費與 90 天退貨保障。',
      file='PaybackAmex_官網_推薦頁實測.png'),
]

if __name__ == '__main__':
    args = sys.argv[1:]
    shots_dir = None
    if '--shots' in args:
        i = args.index('--shots')
        shots_dir = args[i+1]
        args = args[:i] + args[i+2:]
    OUT = args[0] if args else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        check_glyphs(c)
        render = make_table_card if c.get('kind') == 'table' else make_card
        render(c, os.path.join(OUT, c['file']), LABEL, DATE_RANGE)
    if shots_dir:
        vb.LABEL, vb.DATE_RANGE = LABEL, DATE_RANGE
        for sc in SHOT_CARDS:
            src = os.path.join(shots_dir, sc['src'])
            if os.path.exists(src):
                make_shot_card(sc, src, os.path.join(OUT, sc['file']))
            else:
                print('⚠️ 缺截圖原檔，略過：', src)
