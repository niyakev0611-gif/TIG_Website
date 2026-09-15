# -*- coding: utf-8 -*-
"""Visa Bonus 秋季檔（KLICK. BEZAHLT. CASHBACK.）2% 線上回饋 — 主題圖卡產生器
================================================================
承 make_visa_bonus_cards.py（夏季海外檔 7/7–9/1）的版型，
換成秋季線上購物檔 9/15–11/15 的內容。

最大差異：夏季檔只認「德國以外」的消費；秋季檔**只認線上付款、但不限商家國別**，
         德國本地網購（Amazon.de、Zalando…）同樣回饋 2%。

用法：
  python3 make_visa_herbst_cards.py <輸出資料夾>
"""
import os
import sys

from make_weekly_cards import make_card

LABEL = 'Visa Bonus'
DATE_RANGE = '9/15–11/15'  # footer 空間有限，勿放長日期（會撞到右側品牌字）

CARDS = [
 dict(
  theme='#2563EB', badges=[('省錢攻略', True), ('限時活動', False)], illu='bankcard',
  title='網購 2% 現金回饋　不限商家國別',
  subtitle='Visa Bonus 秋季檔｜9/15–11/15　只認線上付款',
  stats=[('2%', '單筆 75 € 以內都回饋'),
         ('15 €', '每人回饋上限')],
  bullets=[
   ('判定基準換了', '夏季檔看消費地點（德國以外才算），秋季檔改看付款方式——只有線上付款才算，實體店刷卡一律不計。'),
   ('好處是不限國別', '商家在哪一國都行，Amazon.de、Zalando 這類德國網店同樣回饋，不必出國；無最低消費，但單筆超過 75 € 整筆不算。'),
   ('何時入帳', '回饋約兩週內直接退回卡片帳戶、最晚 11/30；總預算 65 萬歐元全體共用，用完提前結束。'),
  ],
  takeaway=('省錢提醒', '夏季檔註冊過的人不必重填資料，到 visa.de/bonus 後台一鍵啟用新活動即可；累積 750 € 線上消費就拿滿 15 €。'),
  file='VisaBonusHerbst2026_圖卡1_線上刷卡回饋.png'),
 dict(
  theme='#2E8B57', badges=[('資格檢查', True), ('注意排除', False)], illu='checklist',
  title='誰能拿這筆回饋？',
  subtitle='兩分鐘自我檢查：符合條件、避開排除清單',
  stats=[('18+', '年滿 18、住在德國'),
         ('5 張', '一個帳號最多綁卡數')],
  bullets=[
   ('這些卡可以綁', '德國發行的 Visa 金融卡（Debit）與信用卡都行——DKB、ING、comdirect、Barclays 等家的卡都是 Visa。'),
   ('這些卡直接出局', '預付卡（Prepaid）、V PAY 與 Klarna 發的 Visa 明文排除；N26、BBVA 是 Mastercard，也用不了。'),
   ('這些消費不算', '實體店刷卡、ATM 提款、換匯、儲值、保險與金融服務、博弈投注都排除——回饋只認線上購物。'),
  ],
  takeaway=('版主實測', '版主已在 9/15 啟用這檔活動：官網只填 Email＋卡號、OTP 驗證兩分鐘搞定——完整教學與截圖見網站文章。'),
  file='VisaBonusHerbst2026_圖卡2_誰能參加.png'),
 dict(
  theme='#D4740E', badges=[('實戰技巧', True), ('拆單策略', False)], illu='dealtag',
  title='怎麼把 15 € 領好領滿？',
  subtitle='單筆 75 € 是關鍵——拆單遠比湊單划算',
  stats=[('750 €', '領滿上限所需線上消費'),
         ('75 €', '單筆上限，超過整筆不計')],
  bullets=[
   ('先拆單再結帳', '購物車 120 € 分成兩筆 60 € 各回 1.2 €；硬湊成一筆則一毛都沒有——官方 FAQ 明講 75.01 € 也不給。'),
   ('日常就能刷滿', '超市線上採買、藥妝、外送訂餐、訂票與月費訂閱都算線上付款，兩個月累積 750 € 並不難。'),
   ('別踩這些雷', '結帳要刷「綁定過的那張卡」；PayPal 等錢包若轉成間接扣款可能追蹤不到回饋，直接用卡號付最保險。'),
  ],
  takeaway=('操作提醒', '回饋以卡片帳戶入帳日認列，11/15 前最後幾天的交易可能因入帳延遲落空——想領滿的別拖到最後一週。'),
  file='VisaBonusHerbst2026_圖卡3_領好領滿.png'),
]

if __name__ == '__main__':
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        make_card(c, os.path.join(OUT, c['file']), LABEL, DATE_RANGE)
