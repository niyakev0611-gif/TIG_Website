# -*- coding: utf-8 -*-
"""Visa Bonus 2% 海外回饋 — 主題圖卡產生器
================================================================
產出：
  1. 兩張 Seedling Flat 資訊卡（活動總覽／參加資格）
  2. 四張「截圖框卡」：官方活動頁截圖與版主實測截圖，套上品牌框
     （截圖原檔一次性，用 --shots 指定資料夾；缺檔就只產資訊卡）

用法：
  python3 make_visa_bonus_cards.py <輸出資料夾> [--shots <截圖資料夾>]
"""
import os
import sys
from PIL import Image, ImageDraw

from make_weekly_cards import (make_card, mixed_width, draw_mixed,
                               draw_mixed_vcentered, wrap_mixed, paste_wordmark,
                               BG, CARD, BORDER, TITLE_C, SUB_C, BODY_C, S, W, H)

LABEL = 'Visa Bonus'
DATE_RANGE = '7/7–9/1'  # footer 空間有限，勿放長日期（會撞到右側品牌字）

CARDS = [
 dict(
  theme='#2563EB', badges=[('省錢攻略', True), ('限時活動', False)], illu='bankcard',
  title='Visa 海外刷卡 2% 現金回饋',
  subtitle='Visa Bonus 官方活動｜7/7–9/1 德國以外消費都算',
  stats=[('2%', '單筆 75 € 以內都回饋'),
         ('15 €', '每人回饋上限')],
  bullets=[
   ('怎麼參加', '到 visa.de/bonus 用 Email 註冊（OTP 驗證），綁定最多 5 張德國發行的 Visa 卡——先註冊、後消費才算數。'),
   ('哪些消費算', '德國以外的實體店消費＋國外網購都算，歐元區也行；單筆超過 75 € 整筆不計，大額消費記得拆單。'),
   ('何時入帳', '回饋約兩週內直接退回卡片帳戶；活動總預算 50 萬歐元用完就提前結束，先搶先贏。'),
  ],
  takeaway=('省錢提醒', '暑假出國、跨國網購前花兩分鐘註冊：累積 750 € 合格消費就拿滿 15 €——記得刷「綁定過的那張卡」。'),
  file='VisaBonus2026_圖卡1_海外刷卡回饋.png'),
 dict(
  theme='#2E8B57', badges=[('資格檢查', True), ('注意排除', False)], illu='checklist',
  title='誰能拿這筆回饋？',
  subtitle='兩分鐘自我檢查：符合條件、避開排除清單',
  stats=[('18+', '年滿 18、住在德國'),
         ('5 張', '一個帳號最多綁卡數')],
  bullets=[
   ('這些卡可以綁', '德國發行的 Visa 金融卡（Debit）與信用卡都行——DKB、ING、comdirect、Barclays 等家的卡都是 Visa。'),
   ('這些卡直接出局', '預付卡（Prepaid）、V PAY 與 Klarna 發的 Visa 明文排除；N26、BBVA 是 Mastercard，也用不了。'),
   ('這些消費不算', '德國境內消費、ATM 提款、換匯、儲值、保險與金融服務都不算——回饋只認「國外購物」。'),
  ],
  takeaway=('版主實測', '版主已註冊成功：官網只填 Email＋卡號、OTP 驗證兩分鐘搞定——完整教學與截圖見網站文章。'),
  file='VisaBonus2026_圖卡2_誰能參加.png'),
]

# ── 截圖框卡：官方截圖套品牌框 ──────────────────────────────
SHOT_CARDS = [
 dict(src='crop_hero.png', theme='#2563EB', badge='官方活動頁',
      title='visa.de/bonus 註冊入口長這樣',
      caption='認明 Visa 官方網域再輸入卡號；活動頁點「Jetzt mit Visa Bonus starten」即可開始註冊。',
      file='VisaBonus2026_官網1_活動頁.png'),
 dict(src='crop_aktionen.png', theme='#2563EB', badge='官方活動總覽',
      title='夏季海外刷卡＋秋季網購一次看',
      caption='夏季檔（7/7–9/1）德國以外消費 2%；官方已預告秋季檔（9/15–11/15）線上購物 2%——註冊一次、之後一鍵參加。',
      file='VisaBonus2026_官網2_活動方案.png'),
 dict(src='crop_steps.png', theme='#2563EB', badge='六步驟註冊',
      title='Email＋OTP，兩分鐘完成',
      caption='註冊 → 綁卡（最多 5 張）→ 啟用活動 → 海外刷卡 → 約兩週回饋入帳 → 後台隨時查進度。',
      file='VisaBonus2026_官網3_註冊步驟.png'),
 dict(src='user_registration.png', theme='#2E8B57', badge='版主實測',
      title='版主已綁兩張卡、啟用夏季活動',
      caption='後台只顯示卡號末四碼；啟用「Alltag aus, Cashback an.」後，記得點確認信裡的連結完成註冊。',
      file='VisaBonus2026_版主實測_綁卡完成.png'),
]

def make_shot_card(spec, src_path, out_path):
    theme = spec['theme']
    img = Image.new('RGB', (W*S, H*S), BG)
    d = ImageDraw.Draw(img)
    def R(*v):
        return [x*S for x in v]

    d.rectangle(R(0, 0, W, 40), fill=theme)
    d.rectangle(R(0, H-12, W, H), fill=theme)
    d.rounded_rectangle(R(36, 60, W-36, 1002), radius=28*S, fill=CARD,
                        outline=BORDER, width=2*S)

    tw = mixed_width(spec['badge'], 30*S, bold=True)
    bw = tw/S + 52
    d.rounded_rectangle(R(100, 100, 100+bw, 146), radius=23*S, fill=theme)
    draw_mixed_vcentered(d, R(126, 123), spec['badge'], 30*S, 'white', bold=True)
    paste_wordmark(img)

    tsize = 46
    while mixed_width(spec['title'], tsize*S, bold=True) > 880*S and tsize > 34:
        tsize -= 2
    draw_mixed(d, R(100, 184), spec['title'], tsize*S, TITLE_C, bold=True)

    # 截圖置中（在標題與 footer 之間垂直置中）
    shot = Image.open(src_path).convert('RGB')
    maxw, maxh = 880, 560
    ratio = min(maxw/shot.width, maxh/shot.height)
    nw, nh = round(shot.width*ratio), round(shot.height*ratio)
    cap_lines = wrap_mixed(spec['caption'], 30*S, 840*S)
    block_h = nh + 30 + len(cap_lines)*40
    top = 268 + max(0, (980 - 268 - block_h)//2)
    sx = (W - nw)//2
    shot2 = shot.resize((nw*S, nh*S), Image.LANCZOS)
    img.paste(shot2, (sx*S, top*S))
    d.rectangle(R(sx, top, sx+nw, top+nh), outline=BORDER, width=2*S)

    ty = top + nh + 26
    for line in cap_lines:
        draw_mixed(d, R(W/2, ty), line, 30*S, BODY_C, anchor='center')
        ty += 40

    draw_mixed(d, R(64, 1018), '德國知識小種子', 30*S, SUB_C)
    draw_mixed(d, R(316, 1018), f'{LABEL} · {DATE_RANGE}', 30*S, '#8A8F98')
    draw_mixed(d, R(1016, 1018), 'Das deutsche Wissen', 30*S, SUB_C, anchor='right')

    img = img.resize((W, H), Image.LANCZOS)
    img.save(out_path, 'PNG')
    print('✅', out_path)

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
        make_card(c, os.path.join(OUT, c['file']), LABEL, DATE_RANGE)
    if shots_dir:
        for sc in SHOT_CARDS:
            src = os.path.join(shots_dir, sc['src'])
            if os.path.exists(src):
                make_shot_card(sc, src, os.path.join(OUT, sc['file']))
            else:
                print('⚠️ 缺截圖原檔，略過：', src)
