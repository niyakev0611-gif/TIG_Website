# -*- coding: utf-8 -*-
"""週報圖卡產生器 — 德國知識小種子 Das deutsche Wissen
================================================================
版型：1080x1080、#F8F6F2 背景、白卡、頂部色條、badge、兩格 stats、
右上 Seedling Flat 精緻插畫、圓點 bullets、底部觀察框。2x 超取樣抗鋸齒。
字體：Noto Sans CJK TC（中文）＋ Noto Sans（拉丁/數字）。

設計哲學：scripts/cardgen/design_philosophy_seedling_flat.md
（品牌深藍描邊 #1F2937 是唯一輪廓線；每卡限「主題色＋金＋白」三色系；
　單一焦點細節；奇數韻律元素；分層表達深度、無漸層無透視。）

⚠️ 插畫安全區（嚴禁蓋到或貼近文字，適度留白——用戶 2026/07 W29 要求）：
  - 插畫僅允許出現在右上區塊：x ∈ [762, 922]、y ∈ [ILLU_TOP, ILLU_BOTTOM]
  - 與副標底緣（≈308）垂直間距 ≥ 18px、與 bullets 起點（456）間距 ≥ 8px
  - 新增插畫元件時務必檢查所有元素（含彩紙、陰影）不超出安全區

每週使用：複製本檔尾端 CARDS 範本區塊改內容，或
  from make_weekly_cards import make_card, ILLUS 自行組卡。
  python3 make_weekly_cards.py <輸出資料夾>
"""
import math
from PIL import Image, ImageDraw, ImageFont

S = 2  # supersample
W = H = 1080

# ── 插畫安全區 ──────────────────────────────────────────────
ILLU_CX, ILLU_CY = 842, 386   # 插畫中心
ILLU_TOP, ILLU_BOTTOM = 326, 448  # 垂直邊界（1x 座標）

CJK_R = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
CJK_B = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
LAT_R = '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'
LAT_B = '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'

# macOS fallback（本機字型由 Homebrew 裝在 ~/Library/Fonts，OTF 無 ttc index）
import os as _os
if not _os.path.exists(CJK_R):
    _MAC = _os.path.expanduser('~/Library/Fonts')
    CJK_R = f'{_MAC}/NotoSansCJKtc-Regular.otf'
    CJK_B = f'{_MAC}/NotoSansCJKtc-Bold.otf'
    LAT_R = f'{_MAC}/NotoSans-Regular.ttf'
    LAT_B = f'{_MAC}/NotoSans-Bold.ttf'

_font_cache = {}
def F(path, size, index=None):
    key = (path, size, index)
    if key not in _font_cache:
        if index is not None:
            _font_cache[key] = ImageFont.truetype(path, size, index=index)
        else:
            _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]

def cjk(size, bold=False):
    path = CJK_B if bold else CJK_R
    return F(path, size, index=3 if path.endswith('.ttc') else None)

def lat(size, bold=False):
    return F(LAT_B if bold else LAT_R, size)

def is_cjk_char(ch):
    o = ord(ch)
    return (0x2E80 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or
            0xFF00 <= o <= 0xFFEF or 0x3000 <= o <= 0x303F or
            o in (0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2192, 0xB7))

def segments(text):
    runs = []
    for ch in text:
        c = is_cjk_char(ch)
        if runs and runs[-1][0] == c:
            runs[-1][1] += ch
        else:
            runs.append([c, ch])
    return runs

def mixed_width(text, size, bold=False):
    w = 0
    for c, s in segments(text):
        f = cjk(size, bold) if c else lat(size, bold)
        w += f.getlength(s)
    return w

def draw_mixed(d, xy, text, size, fill, bold=False, anchor='left'):
    """逐段切換 CJK / Latin 字體，共用 CJK baseline。anchor: left/center/right"""
    x, y = xy
    total = mixed_width(text, size, bold)
    if anchor == 'center':
        x -= total / 2
    elif anchor == 'right':
        x -= total
    ascent = cjk(size, bold).getmetrics()[0]
    base = y + ascent
    for c, s in segments(text):
        f = cjk(size, bold) if c else lat(size, bold)
        d.text((x, base), s, font=f, fill=fill, anchor='ls')
        x += f.getlength(s)
    return total

def wrap_mixed(text, size, max_w, bold=False):
    """混排斷行：CJK 逐字可斷、拉丁字詞不拆、中式禁則。"""
    units, cur = [], ''
    for ch in text:
        if is_cjk_char(ch):
            if cur:
                units.append(cur); cur = ''
            units.append(ch)
        else:
            if ch == ' ':
                units.append(cur + ch); cur = ''
            else:
                cur += ch
    if cur:
        units.append(cur)
    OPEN, CLOSE = '（「『【〈', '）」』】〉，。、；：！？—'
    merged = []
    for u in units:
        if merged and merged[-1] and merged[-1][-1] in OPEN:
            merged[-1] += u
        elif u and u[0] in CLOSE and merged:
            merged[-1] += u
        else:
            merged.append(u)
    lines, line = [], ''
    for u in merged:
        cand = line + u
        if line and mixed_width(cand.rstrip(), size, bold) > max_w:
            lines.append(line.rstrip())
            line = u.lstrip()
        else:
            line = cand
    if line.strip():
        lines.append(line.rstrip())
    return lines

def mixed_vbbox(text, size, bold=False):
    """整段文字相對 baseline 的視覺上下緣（逐段取各字體實際 bbox）"""
    top, bot = 1e9, -1e9
    for c, s in segments(text):
        f = cjk(size, bold) if c else lat(size, bold)
        asc = f.getmetrics()[0]
        bb = f.getbbox(s)
        if bb[3] > bb[1]:
            top = min(top, bb[1] - asc)
            bot = max(bot, bb[3] - asc)
    if top > bot:
        return 0, 0
    return top, bot

def draw_mixed_vcentered(d, xy, text, size, fill, bold=False, anchor='left'):
    """以字面實際 bbox 對 y_mid 垂直置中——badge 等「框內文字」一律用這個，
    別用 draw_mixed 手動加 offset（CJK baseline 偏低，肉眼會覺得字沉底）。"""
    x, y_mid = xy
    top, bot = mixed_vbbox(text, size, bold)
    base = y_mid - (top + bot) / 2
    return draw_mixed(d, (x, base - cjk(size, bold).getmetrics()[0]),
                      text, size, fill, bold, anchor)

def tint(hexcolor, alpha):
    hexcolor = hexcolor.lstrip('#')
    r, g, b = (int(hexcolor[i:i+2], 16) for i in (0, 2, 4))
    return (round(255*(1-alpha)+r*alpha), round(255*(1-alpha)+g*alpha), round(255*(1-alpha)+b*alpha))

def shade(hexcolor, f):
    hexcolor = hexcolor.lstrip('#')
    r, g, b = (int(hexcolor[i:i+2], 16) for i in (0, 2, 4))
    return (round(r*f), round(g*f), round(b*f))

def star_pts(cx, cy, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n*2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i*180/n)
        pts += [cx + r*math.cos(a), cy + r*math.sin(a)]
    return pts

# ── 品牌 lockup（右上角：手寫字＋小6圈底線＋🌱）─────────────
# 用戶 2026/07 以 Claude Design 定稿：assets/images/Social Media/brand_手寫風.png，
# 經 prep_brand_lockup.py 去背輸出 brand_lockup.png（本資料夾）。
# 之後所有圖卡右上角一律貼這個 lockup，勿用 Noto 印刷體；原稿更新後
# 重跑 prep_brand_lockup.py ＋ 重產圖卡即可。
_WORDMARK = None
def paste_wordmark(img, right=980, top=102, width=365):
    """右緣對齊 right、頂緣 top、寬 width（皆 1x 座標）"""
    global _WORDMARK
    if _WORDMARK is None:
        _WORDMARK = Image.open(_os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), 'brand_lockup.png')).convert('RGBA')
    w = width * S
    h = round(_WORDMARK.height * w / _WORDMARK.width)
    wm = _WORDMARK.resize((w, h), Image.LANCZOS)
    img.paste(wm, (right * S - w, top * S), wm)

# ── 色彩常數 ────────────────────────────────────────────────
BG      = '#F8F6F2'
CARD    = '#FFFFFF'
BORDER  = '#E8E4DE'
TITLE_C = '#1F2937'
SUB_C   = '#6B7280'
BODY_C  = '#374151'
STATBG  = '#EFECE5'
FOOT_C  = '#8A8F98'
OUTLINE = '#1F2937'          # 插畫唯一輪廓色（品牌筆跡）
GOLD, GOLD_D, GOLD_HI = '#F0C24B', '#D9A72E', '#FBE7AD'

# ════════════════════════════════════════════════════════════
# Seedling Flat 插畫元件庫
# 每個函式簽名：illu_xxx(d, R, S, cx, cy, theme)
# cx, cy 一律傳 ILLU_CX, ILLU_CY；所有元素須落在安全區內。
# ════════════════════════════════════════════════════════════

def _dots(d, R, cx, cy, spots):
    """韻律元素：奇數顆、大小遞減的圓點"""
    for (dx, dy, r, col) in spots:
        d.ellipse(R(cx+dx-r, cy+dy-r, cx+dx+r, cy+dy+r), fill=col)

def illu_podium(d, R, S, cx, cy, theme):
    """麥克風講台（記者會／演說／官方聲明）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-62, -34, 4, theme), (-44, -52, 3, GOLD),
                         (42, -52, 4, tint(theme, 0.5)), (64, -28, 3, GOLD),
                         (70, 8, 3, theme)))
    d.ellipse(R(cx-40, cy+50, cx+46, cy+62), fill=tint(theme, 0.18))
    # 講台：檯面＋兩層檯身＋面板
    d.rounded_rectangle(R(cx-52, cy+12, cx+52, cy+58), radius=9*S, fill=tint(theme, 0.25), outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-58, cy+2, cx+58, cy+16), radius=7*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-36, cy+28, cx+36, cy+38), radius=5*S, fill=tint(theme, 0.5))
    # 麥克風
    d.line(R(cx, cy-10, cx, cy+2), fill=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-12, cy-52, cx+12, cy-10), radius=12*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-7, cy-46, cx-2, cy-22), radius=3*S, fill=tint(theme, 0.45))
    # 聲波（焦點細節）
    for dx in (-1, 1):
        d.arc(R(cx+dx*30-13, cy-44, cx+dx*30+13, cy-18),
              start=-65 if dx > 0 else 115, end=65 if dx > 0 else 245, fill=theme, width=ow)

def illu_flags(d, R, S, cx, cy, theme):
    """德法雙旗（雙邊外交／峰會）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -6, 3, theme), (0, -56, 3, GOLD), (70, -6, 3, theme)))
    d.ellipse(R(cx-48, cy+48, cx+48, cy+60), fill=tint(theme, 0.18))
    for px, flag_x1, flag_x2, cols, vert in (
            (-14, -66, -14, ('#1F2937', '#C0392B', '#E8B70A'), False),
            (14, 14, 66, ('#2563EB', '#FFFFFF', '#C0392B'), True)):
        x1, x2, y1, y2 = cx+flag_x1, cx+flag_x2, cy-50, cy-14
        if vert:
            w3 = (x2-x1)/3
            for i, c in enumerate(cols):
                d.rectangle(R(x1+i*w3, y1, x1+(i+1)*w3, y2), fill=c)
        else:
            h3 = (y2-y1)/3
            for i, c in enumerate(cols):
                d.rectangle(R(x1, y1+i*h3, x2, y1+(i+1)*h3), fill=c)
        d.rectangle(R(x1, y1, x2, y2), outline=OUTLINE, width=ow)
        d.line(R(cx+px, y1, cx+px, cy+50), fill=OUTLINE, width=ow)
        d.ellipse(R(cx+px-5, cy-58, cx+px+5, cy-48), fill=GOLD, outline=OUTLINE, width=3*S)
        d.ellipse(R(cx+px-8, cy+46, cx+px+8, cy+56), fill=OUTLINE)
    # 焦點細節：兩旗之間的金星
    d.polygon(R(*star_pts(cx, cy+14, 10, 4)), fill=GOLD, outline=OUTLINE)

def illu_coins(d, R, S, cx, cy, theme):
    """金幣＋上升箭頭（預算／財政／物價）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, -42, 3, theme), (36, -50, 3, GOLD), (68, 12, 3, GOLD_D)))
    d.ellipse(R(cx-52, cy+46, cx+42, cy+60), fill=tint(theme, 0.18))
    # 硬幣堆（交錯色）
    for i, yy in enumerate((34, 12, -10)):
        d.rounded_rectangle(R(cx-62, cy+yy-11, cx-2, cy+yy+13), radius=12*S,
                            fill=GOLD if i % 2 else GOLD_D, outline=OUTLINE, width=ow)
    # 立起的 € 硬幣（焦點細節：內圈＋高光）
    ex, ey, er = cx-32, cy-32, 22
    d.ellipse(R(ex-er, ey-er, ex+er, ey+er), fill=GOLD, outline=OUTLINE, width=ow)
    d.ellipse(R(ex-er+7, ey-er+7, ex+er-7, ey+er-7), outline=GOLD_D, width=3*S)
    d.arc(R(ex-er+4, ey-er+4, ex+er-4, ey+er-4), start=195, end=250, fill=GOLD_HI, width=4*S)
    draw_mixed(d, R(ex, ey-16), '€', 26*S, OUTLINE, bold=True, anchor='center')
    # 上升箭頭
    d.line(R(cx+8, cy+34, cx+54, cy-20), fill=theme, width=ow+2*S)
    d.polygon(R(cx+38, cy-26, cx+62, cy-32, cx+54, cy-6), fill=theme)

def illu_idcard(d, R, S, cx, cy, theme):
    """居留卡＋晶片＋指紋（居留／簽證／入籍）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-64, -54, 3, GOLD), (0, -58, 3, tint(theme, 0.5)), (64, -54, 3, GOLD)))
    d.ellipse(R(cx-56, cy+48, cx+56, cy+60), fill=tint(theme, 0.18))
    # 卡片本體＋色帶
    d.rounded_rectangle(R(cx-70, cy-44, cx+70, cy+44), radius=12*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-70, cy-44, cx+70, cy-22), radius=12*S, fill=theme)
    d.rectangle(R(cx-70, cy-34, cx+70, cy-22), fill=theme)
    d.rounded_rectangle(R(cx-70, cy-44, cx+70, cy+44), radius=12*S, outline=OUTLINE, width=ow)
    d.ellipse(R(cx+52, cy-37, cx+60, cy-29), fill='white')
    # 大頭照
    d.rounded_rectangle(R(cx-54, cy-10, cx-18, cy+30), radius=6*S, fill=tint(theme, 0.25), outline=OUTLINE, width=3*S)
    d.ellipse(R(cx-43, cy-2, cx-29, cy+12), fill=tint(theme, 0.7))
    d.arc(R(cx-47, cy+10, cx-25, cy+32), start=180, end=360, fill=tint(theme, 0.7), width=6*S)
    # 晶片（eAT 的靈魂）
    d.rounded_rectangle(R(cx-6, cy-12, cx+14, cy+2), radius=3*S, fill=GOLD, outline=OUTLINE, width=3*S)
    d.line(R(cx+4, cy-12, cx+4, cy+2), fill=OUTLINE, width=2*S)
    # 資料線
    for yy, x2 in ((14, 30), (26, 18)):
        d.line(R(cx-6, cy+yy, cx+x2, cy+yy), fill='#9CA3AF', width=4*S)
    # 焦點細節：指紋
    fx, fy = cx+46, cy+18
    for r in (17, 10, 4):
        d.arc(R(fx-r, fy-r, fx+r, fy+r), start=-60, end=200, fill=theme, width=4*S)

def illu_camera(d, R, S, cx, cy, theme):
    """監視器＋人臉辨識框（監控／內政／治安）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, 14, 3, GOLD), (56, -44, 3, tint(theme, 0.5)), (68, 0, 3, theme)))
    # 掃描光束（畫在最底層）
    d.polygon(R(cx+14, cy-10, cx+38, cy+34, cx-16, cy+34), fill=tint(theme, 0.12))
    # 壁掛座＋支架
    d.rounded_rectangle(R(cx-66, cy-56, cx-52, cy-42), radius=4*S, fill=theme, outline=OUTLINE, width=3*S)
    d.line(R(cx-58, cy-48, cx-30, cy-30), fill=OUTLINE, width=ow)
    # 機身＋高光＋鏡頭
    d.rounded_rectangle(R(cx-50, cy-36, cx+22, cy-2), radius=9*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-42, cy-30, cx-22, cy-23), radius=3*S, fill=tint(theme, 0.45))
    d.ellipse(R(cx+2, cy-30, cx+24, cy-8), fill='white', outline=OUTLINE, width=ow)
    d.ellipse(R(cx+9, cy-23, cx+17, cy-15), fill=OUTLINE)
    d.ellipse(R(cx+3.5, cy-25, cx+7.5, cy-21), fill=GOLD)
    # 焦點細節：人臉＋偵測框
    fx, fy, r = cx+8, cy+30, 17
    d.ellipse(R(fx-r, fy-r, fx+r, fy+r), fill=tint(theme, 0.2), outline=OUTLINE, width=3*S)
    d.ellipse(R(fx-8, fy-5, fx-3, fy), fill=OUTLINE)
    d.ellipse(R(fx+3, fy-5, fx+8, fy), fill=OUTLINE)
    d.arc(R(fx-7, fy+3, fx+7, fy+13), start=20, end=160, fill=OUTLINE, width=3*S)
    b, l = 28, 11
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, y0 = fx+sx*b, fy+sy*b
            d.line(R(x0, y0, x0-sx*l, y0), fill=theme, width=ow)
            d.line(R(x0, y0, x0, y0-sy*l), fill=theme, width=ow)

def illu_trophy(d, R, S, cx, cy, theme):
    """獎盃＋足球（賽事／冠軍）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-60, -46, 5, theme), (-30, -58, 4, GOLD),
                         (22, -56, 5, tint(theme, 0.5)), (60, -40, 4, GOLD_D),
                         (70, -2, 3, theme)))
    d.ellipse(R(cx-42, cy+46, cx+58, cy+60), fill=tint(theme, 0.18))
    # 把手（先畫，盃身壓住內端）
    d.arc(R(cx-58, cy-46, cx-24, cy-10), start=80, end=280, fill=OUTLINE, width=ow)
    d.arc(R(cx+24, cy-46, cx+58, cy-10), start=-100, end=100, fill=OUTLINE, width=ow)
    # 盃身：直壁＋碗形底
    d.rectangle(R(cx-34, cy-50, cx+34, cy-18), fill=GOLD)
    d.pieslice(R(cx-34, cy-42, cx+34, cy+6), start=0, end=180, fill=GOLD)
    d.arc(R(cx-34, cy-42, cx+34, cy+6), start=0, end=180, fill=OUTLINE, width=ow)
    d.line(R(cx-34, cy-50, cx-34, cy-18), fill=OUTLINE, width=ow)
    d.line(R(cx+34, cy-50, cx+34, cy-18), fill=OUTLINE, width=ow)
    # 刻面高光
    d.rounded_rectangle(R(cx-25, cy-42, cx-15, cy-4), radius=5*S, fill=GOLD_HI)
    # 盃口飾帶
    d.rounded_rectangle(R(cx-40, cy-58, cx+40, cy-44), radius=7*S, fill=GOLD_D, outline=OUTLINE, width=ow)
    # 焦點細節：主題色星形
    d.polygon(R(*star_pts(cx+2, cy-22, 12, 5)), fill=theme, outline=OUTLINE)
    # 盃腳＋雙層底座
    d.polygon(R(cx-8, cy+4, cx+8, cy+4, cx+13, cy+20, cx-13, cy+20), fill=GOLD_D, outline=OUTLINE)
    d.rounded_rectangle(R(cx-26, cy+20, cx+26, cy+33), radius=5*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-33, cy+31, cx+33, cy+44), radius=5*S, fill=shade(theme, 0.72), outline=OUTLINE, width=ow)
    # 足球（前景、分層表達深度）
    bx, by, r = cx+50, cy+24, 22
    d.ellipse(R(bx-r, by-r, bx+r, by+r), fill='white', outline=OUTLINE, width=ow)
    pent = []
    for i in range(5):
        a = math.radians(-90 + i*72)
        pent += [bx + 8*math.cos(a), by + 8*math.sin(a)]
        d.line(R(bx + 8*math.cos(a), by + 8*math.sin(a),
                 bx + 19*math.cos(a), by + 19*math.sin(a)), fill=OUTLINE, width=3*S)
    d.polygon(R(*pent), fill=OUTLINE)

def illu_bankcard(d, R, S, cx, cy, theme):
    """銀行卡＋感應波＋歐元金幣（刷卡／現金回饋／支付）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-64, -48, 3, GOLD), (52, -54, 3, tint(theme, 0.5)), (72, -12, 3, theme)))
    d.ellipse(R(cx-56, cy+42, cx+50, cy+56), fill=tint(theme, 0.18))
    # 卡片本體＋頂部高光條
    d.rounded_rectangle(R(cx-66, cy-40, cx+42, cy+30), radius=10*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-58, cy-32, cx-18, cy-25), radius=3*S, fill=tint(theme, 0.45))
    # 晶片
    d.rounded_rectangle(R(cx-56, cy-12, cx-36, cy+2), radius=3*S, fill=GOLD, outline=OUTLINE, width=3*S)
    d.line(R(cx-46, cy-12, cx-46, cy+2), fill=OUTLINE, width=2*S)
    # 感應波（卡右上）
    for r in (8, 15):
        d.arc(R(cx+16-r, cy-18-r, cx+16+r, cy-18+r), start=-40, end=40, fill='white', width=4*S)
    # 卡號線
    d.line(R(cx-56, cy+14, cx-8, cy+14), fill=tint(theme, 0.55), width=5*S)
    # 焦點細節：€ 金幣（回饋入帳）
    ex, ey, er = cx+42, cy+20, 24
    d.ellipse(R(ex-er, ey-er, ex+er, ey+er), fill=GOLD, outline=OUTLINE, width=ow)
    d.ellipse(R(ex-er+7, ey-er+7, ex+er-7, ey+er-7), outline=GOLD_D, width=3*S)
    d.arc(R(ex-er+4, ey-er+4, ex+er-4, ey+er-4), start=195, end=250, fill=GOLD_HI, width=4*S)
    draw_mixed(d, R(ex, ey-17), '€', 28*S, OUTLINE, bold=True, anchor='center')

def illu_checklist(d, R, S, cx, cy, theme):
    """資格清單板（條件檢查／申請資格）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, -40, 3, GOLD), (58, -50, 3, tint(theme, 0.5)), (72, 2, 3, theme)))
    d.ellipse(R(cx-54, cy+44, cx+50, cy+58), fill=tint(theme, 0.18))
    # 板身＋夾子
    d.rounded_rectangle(R(cx-54, cy-44, cx+40, cy+44), radius=8*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-22, cy-52, cx+8, cy-38), radius=5*S, fill=theme, outline=OUTLINE, width=3*S)
    d.ellipse(R(cx-11, cy-49, cx-3, cy-41), fill='white', outline=OUTLINE, width=2*S)
    # 三列：兩勾一叉
    for dy, ok in ((-24, True), (0, True), (24, False)):
        bx1, by1 = cx-44, cy+dy-7
        d.rounded_rectangle(R(bx1, by1, bx1+14, by1+14), radius=3*S,
                            fill=theme if ok else 'white', outline=OUTLINE, width=3*S)
        if ok:
            d.line(R(bx1+3, by1+7, bx1+6, by1+11), fill='white', width=3*S)
            d.line(R(bx1+6, by1+11, bx1+11, by1+3), fill='white', width=3*S)
        else:
            d.line(R(bx1+4, by1+4, bx1+10, by1+10), fill=OUTLINE, width=3*S)
            d.line(R(bx1+10, by1+4, bx1+4, by1+10), fill=OUTLINE, width=3*S)
        d.line(R(bx1+22, by1+7, cx+28, by1+7), fill=tint(theme, 0.5), width=4*S)
    # 焦點細節：金色核可徽章
    bx, by, br = cx+42, cy+28, 20
    d.ellipse(R(bx-br, by-br, bx+br, by+br), fill=GOLD, outline=OUTLINE, width=ow)
    d.line(R(bx-8, by+1, bx-2, by+8), fill=OUTLINE, width=4*S)
    d.line(R(bx-2, by+8, bx+9, by-6), fill=OUTLINE, width=4*S)

def illu_noalcohol(d, R, S, cx, cy, theme):
    """酒瓶＋禁止環（禁酒令／站內管制）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, -30, 4, GOLD), (58, -46, 3, tint(theme, 0.5)),
                         (68, 20, 3, theme)))
    d.ellipse(R(cx-40, cy+46, cx+40, cy+58), fill=tint(theme, 0.18))
    # 酒瓶：瓶身＋瓶頸＋瓶蓋＋金色酒標
    d.rounded_rectangle(R(cx-19, cy-4, cx+19, cy+40), radius=8*S, fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    d.rectangle(R(cx-7, cy-28, cx+7, cy-2), fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-9, cy-38, cx+9, cy-27), radius=3*S, fill=GOLD, outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-15, cy+8, cx+15, cy+26), radius=4*S, fill=GOLD, outline=OUTLINE, width=3*S)
    # 禁止環＋斜槓（焦點細節）
    r = 50
    d.ellipse(R(cx-r, cy-r+2, cx+r, cy+r+2), outline=theme, width=ow+3*S)
    d.line(R(cx-36, cy+38, cx+36, cy-34), fill=theme, width=ow+3*S)

def illu_carehand(d, R, S, cx, cy, theme):
    """雙手托愛心＋白十字（照護／護理保險）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-64, -42, 4, GOLD), (0, -56, 3, tint(theme, 0.5)),
                         (58, -46, 4, theme), (70, -6, 3, GOLD)))
    d.ellipse(R(cx-50, cy+48, cx+50, cy+60), fill=tint(theme, 0.18))
    # 托手（下方碗形雙手）
    d.pieslice(R(cx-52, cy+4, cx+52, cy+60), start=0, end=180, fill=tint(theme, 0.28), outline=OUTLINE, width=ow)
    for dx in (-26, 0, 26):
        d.line(R(cx+dx, cy+32, cx+dx, cy+48), fill=OUTLINE, width=3*S)
    # 愛心（金色，雙圓弧＋三角身）
    hy = cy - 6
    d.pieslice(R(cx-28, hy-24, cx, hy+4), start=180, end=360, fill=GOLD)
    d.pieslice(R(cx, hy-24, cx+28, hy+4), start=180, end=360, fill=GOLD)
    d.polygon(R(cx-27, hy-10, cx+27, hy-10, cx, hy+26), fill=GOLD)
    d.arc(R(cx-28, hy-24, cx, hy+4), start=180, end=360, fill=OUTLINE, width=ow)
    d.arc(R(cx, hy-24, cx+28, hy+4), start=180, end=360, fill=OUTLINE, width=ow)
    d.line(R(cx-27, hy-10, cx, hy+26), fill=OUTLINE, width=ow)
    d.line(R(cx+27, hy-10, cx, hy+26), fill=OUTLINE, width=ow)
    # 白十字（焦點細節）
    d.line(R(cx, hy-5, cx, hy+13), fill='white', width=5*S)
    d.line(R(cx-9, hy+4, cx+9, hy+4), fill='white', width=5*S)

def illu_contract(d, R, S, cx, cy, theme):
    """協約文件＋簽名＋金印（團體協約／官方方案）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, -44, 3, GOLD), (54, -52, 3, tint(theme, 0.5)),
                         (70, 2, 3, theme)))
    d.ellipse(R(cx-48, cy+46, cx+52, cy+58), fill=tint(theme, 0.18))
    # 紙張本體（右上折角）
    x1, y1, x2, y2 = cx-46, cy-46, cx+40, cy+46
    fold = 16
    d.polygon(R(x1, y1, x2-fold, y1, x2, y1+fold, x2, y2, x1, y2), fill='white', outline=OUTLINE, width=ow)
    d.line(R(x2-fold, y1, x2-fold, y1+fold), fill=OUTLINE, width=3*S)
    d.line(R(x2-fold, y1+fold, x2, y1+fold), fill=OUTLINE, width=3*S)
    # 標題色塊＋內文線
    d.rounded_rectangle(R(x1+13, y1+13, x1+50, y1+21), radius=3*S, fill=theme)
    for i, yy in enumerate((y1+34, y1+46)):
        d.line(R(x1+13, yy, x2-16, yy), fill='#9CA3AF', width=4*S)
    d.line(R(x1+13, y1+58, cx+6, y1+58), fill='#9CA3AF', width=4*S)
    # 簽名 swoosh（焦點細節）
    d.line(R(x1+13, y2-22, x1+28, y2-30), fill=theme, width=4*S)
    d.arc(R(x1+24, y2-36, x1+46, y2-16), start=110, end=360, fill=theme, width=4*S)
    # 金印（右下）
    sx, sy, sr = x2-4, y2-6, 15
    d.ellipse(R(sx-sr, sy-sr, sx+sr, sy+sr), fill=GOLD, outline=OUTLINE, width=ow)
    d.polygon(R(*star_pts(sx, sy, 8, 3.4)), fill=theme, outline=OUTLINE)

def illu_reichstag(d, R, S, cx, cy, theme):
    """國會大廈（國會／內閣人事／立法）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, -36, 3, GOLD), (58, -48, 3, tint(theme, 0.5)),
                         (72, -8, 3, theme)))
    d.ellipse(R(cx-58, cy+46, cx+58, cy+58), fill=tint(theme, 0.18))
    # 基座台階
    d.rounded_rectangle(R(cx-66, cy+36, cx+66, cy+48), radius=4*S,
                        fill=tint(theme, 0.25), outline=OUTLINE, width=3*S)
    # 柱廊：5 根柱（奇數韻律）
    for dx in (-48, -24, 0, 24, 48):
        d.rectangle(R(cx+dx-6, cy+2, cx+dx+6, cy+36), fill='white', outline=OUTLINE, width=3*S)
    # 簷部橫樑＋金星
    d.rounded_rectangle(R(cx-62, cy-14, cx+62, cy+4), radius=4*S, fill=theme, outline=OUTLINE, width=ow)
    d.polygon(R(*star_pts(cx, cy-5, 7, 3)), fill=GOLD, outline=OUTLINE)
    # 玻璃圓頂（焦點細節）＋肋線＋橫箍
    d.pieslice(R(cx-30, cy-44, cx+30, cy+16), start=180, end=360,
               fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    for dx, top in ((-15, -38), (0, -42), (15, -38)):
        d.line(R(cx+dx, cy-16, cx+dx, cy+top+2), fill=OUTLINE, width=3*S)
    d.arc(R(cx-30, cy-44, cx+30, cy+16), start=200, end=340, fill=OUTLINE, width=3*S)
    # 頂端金球
    d.line(R(cx, cy-52, cx, cy-44), fill=OUTLINE, width=3*S)
    d.ellipse(R(cx-5, cy-58, cx+5, cy-48), fill=GOLD, outline=OUTLINE, width=3*S)

def illu_candle(d, R, S, cx, cy, theme):
    """悼念蠟燭＋愛心（追悼／重大社會事件）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-64, -40, 3, GOLD), (52, -52, 3, tint(theme, 0.5)),
                         (70, -10, 3, theme)))
    d.ellipse(R(cx-52, cy+46, cx+54, cy+58), fill=tint(theme, 0.18))
    # 小蠟燭（後層）
    d.rounded_rectangle(R(cx-58, cy+10, cx-30, cy+44), radius=5*S, fill='white')
    d.rectangle(R(cx-58, cy+24, cx-30, cy+32), fill=tint(theme, 0.30))
    d.rounded_rectangle(R(cx-58, cy+10, cx-30, cy+44), radius=5*S, outline=OUTLINE, width=ow)
    d.line(R(cx-44, cy+2, cx-44, cy+10), fill=OUTLINE, width=3*S)
    d.ellipse(R(cx-49, cy-12, cx-39, cy+2), fill=GOLD, outline=OUTLINE, width=3*S)
    # 主蠟燭
    d.rounded_rectangle(R(cx-14, cy-14, cx+18, cy+44), radius=6*S, fill='white')
    d.rectangle(R(cx-14, cy+4, cx+18, cy+14), fill=tint(theme, 0.30))
    d.rounded_rectangle(R(cx-14, cy-14, cx+18, cy+44), radius=6*S, outline=OUTLINE, width=ow)
    d.line(R(cx+2, cy-22, cx+2, cy-14), fill=OUTLINE, width=3*S)
    # 火焰（焦點細節：金色外焰＋亮色內焰）＋光暈弧
    d.ellipse(R(cx-7, cy-46, cx+11, cy-20), fill=GOLD, outline=OUTLINE, width=3*S)
    d.ellipse(R(cx-2, cy-38, cx+6, cy-26), fill=GOLD_HI)
    d.arc(R(cx-17, cy-54, cx+21, cy-16), start=210, end=330, fill=GOLD_D, width=3*S)
    # 主題色愛心（右側前景）
    hx, hy = cx+48, cy+24
    d.pieslice(R(hx-16, hy-14, hx, hy+2), start=180, end=360, fill=theme)
    d.pieslice(R(hx, hy-14, hx+16, hy+2), start=180, end=360, fill=theme)
    d.polygon(R(hx-15, hy-6, hx+15, hy-6, hx, hy+14), fill=theme)
    d.arc(R(hx-16, hy-14, hx, hy+2), start=180, end=360, fill=OUTLINE, width=3*S)
    d.arc(R(hx, hy-14, hx+16, hy+2), start=180, end=360, fill=OUTLINE, width=3*S)
    d.line(R(hx-15, hy-6, hx, hy+14), fill=OUTLINE, width=3*S)
    d.line(R(hx+15, hy-6, hx, hy+14), fill=OUTLINE, width=3*S)

def illu_briefcase(d, R, S, cx, cy, theme):
    """公事包＋放大鏡（就業／勞動市場／求職）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-64, -44, 3, GOLD), (54, -52, 3, tint(theme, 0.5)),
                         (72, -14, 3, theme)))
    d.ellipse(R(cx-54, cy+42, cx+52, cy+56), fill=tint(theme, 0.18))
    # 提把（先畫，包身壓住下端）
    d.rounded_rectangle(R(cx-28, cy-38, cx+12, cy-10), radius=10*S, outline=OUTLINE, width=ow)
    # 包身＋頂部高光條
    d.rounded_rectangle(R(cx-62, cy-18, cx+46, cy+40), radius=10*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-54, cy-11, cx-20, cy-4), radius=3*S, fill=tint(theme, 0.45))
    # 中線與金釦
    d.line(R(cx-62, cy+10, cx+46, cy+10), fill=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-16, cy+2, cx, cy+18), radius=3*S, fill=GOLD, outline=OUTLINE, width=3*S)
    # 焦點細節：放大鏡（求職搜尋）
    gx, gy, gr = cx+52, cy+12, 20
    d.ellipse(R(gx-gr, gy-gr, gx+gr, gy+gr), fill='white', outline=OUTLINE, width=ow)
    d.ellipse(R(gx-gr+6, gy-gr+6, gx+gr-6, gy+gr-6), fill=tint(theme, 0.15))
    d.arc(R(gx-gr+4, gy-gr+4, gx+gr-4, gy+gr-4), start=195, end=250, fill='white', width=4*S)
    d.line(R(gx+13, gy+13, gx+26, gy+26), fill=OUTLINE, width=ow+2*S)

def illu_drone(d, R, S, cx, cy, theme):
    """四旋翼無人機＋掛載包裹（無人機事件／空域安全）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -46, 3, GOLD), (60, -50, 3, tint(theme, 0.5)),
                         (72, 6, 3, theme)))
    d.ellipse(R(cx-46, cy+46, cx+46, cy+58), fill=tint(theme, 0.18))
    # 機臂（先畫，機身壓住中央接點）
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        d.line(R(cx, cy-6, cx+sx*46, cy-6+sy*20), fill=OUTLINE, width=ow+2*S)
    # 四具旋翼：淺色槳盤＋深色軸心
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        rx, ry = cx+sx*46, cy-6+sy*20
        d.ellipse(R(rx-17, ry-6, rx+17, ry+6), fill=tint(theme, 0.30), outline=OUTLINE, width=3*S)
        d.ellipse(R(rx-4, ry-4, rx+4, ry+4), fill=OUTLINE)
    # 機身＋頂部高光條
    d.rounded_rectangle(R(cx-24, cy-18, cx+24, cy+8), radius=8*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-17, cy-12, cx+1, cy-6), radius=3*S, fill=tint(theme, 0.45))
    # 鏡頭
    d.ellipse(R(cx+4, cy-8, cx+18, cy+2), fill='white', outline=OUTLINE, width=3*S)
    # 焦點細節：掛載的金色包裹（可疑裝置）
    d.line(R(cx-10, cy+8, cx-10, cy+16), fill=OUTLINE, width=3*S)
    d.line(R(cx+10, cy+8, cx+10, cy+16), fill=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-18, cy+16, cx+18, cy+40), radius=5*S, fill=GOLD, outline=OUTLINE, width=ow)
    d.line(R(cx, cy+16, cx, cy+40), fill=GOLD_D, width=3*S)
    d.line(R(cx-18, cy+27, cx+18, cy+27), fill=GOLD_D, width=3*S)

def illu_lowwater(d, R, S, cx, cy, theme):
    """水位標尺＋擱淺貨船（河川低水位／內河航運）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -44, 3, GOLD), (44, -50, 3, tint(theme, 0.5)),
                         (72, -18, 3, theme)))
    # 乾涸河床（底層淺色）
    d.rounded_rectangle(R(cx-72, cy+16, cx+72, cy+48), radius=8*S, fill=tint(theme, 0.14))
    # 低水位水體（僅剩薄薄一層）
    d.rounded_rectangle(R(cx-72, cy+32, cx+72, cy+48), radius=8*S,
                        fill=tint(theme, 0.42), outline=OUTLINE, width=3*S)
    # 貨船：船身＋駕駛艙＋金色貨櫃
    d.polygon(R(cx-58, cy+2, cx+30, cy+2, cx+18, cy+32, cx-46, cy+32), fill=theme)
    d.line(R(cx-58, cy+2, cx+30, cy+2), fill=OUTLINE, width=ow)
    d.line(R(cx+30, cy+2, cx+18, cy+32), fill=OUTLINE, width=ow)
    d.line(R(cx+18, cy+32, cx-46, cy+32), fill=OUTLINE, width=ow)
    d.line(R(cx-46, cy+32, cx-58, cy+2), fill=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-56, cy-18, cx-32, cy+2), radius=4*S, fill='white', outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-20, cy-14, cx+12, cy+2), radius=4*S, fill=GOLD, outline=OUTLINE, width=3*S)
    # 焦點細節：水位標尺（刻度＋指向低水位的金色三角）
    px1, px2 = cx+44, cy
    d.rounded_rectangle(R(px1, cy-46, px1+16, cy+44), radius=4*S, fill='white', outline=OUTLINE, width=ow)
    for dy in (-34, -22, -10, 2, 14, 26):
        d.line(R(px1+3, cy+dy, px1+10, cy+dy), fill=OUTLINE, width=2*S)
    d.polygon(R(px1+30, cy+22, px1+30, cy+38, px1+18, cy+30), fill=GOLD, outline=OUTLINE, width=3*S)

def illu_ballotbox(d, R, S, cx, cy, theme):
    """投票箱＋選票（選舉／民調）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-68, -34, 3, GOLD), (58, -46, 3, tint(theme, 0.5)),
                         (72, 4, 3, theme)))
    d.ellipse(R(cx-54, cy+46, cx+54, cy+58), fill=tint(theme, 0.18))
    # 選票（後層，正要投入）
    d.rounded_rectangle(R(cx-20, cy-52, cx+22, cy-2), radius=5*S, fill='white', outline=OUTLINE, width=ow)
    d.line(R(cx-11, cy-42, cx+13, cy-42), fill=tint(theme, 0.5), width=4*S)
    d.line(R(cx-11, cy-22, cx+13, cy-22), fill=tint(theme, 0.5), width=4*S)
    # 焦點細節：選票上的金色勾選格
    d.rounded_rectangle(R(cx-14, cy-36, cx-2, cy-24), radius=3*S, fill=GOLD, outline=OUTLINE, width=3*S)
    d.line(R(cx-11, cy-30, cx-8, cy-26), fill=OUTLINE, width=3*S)
    d.line(R(cx-8, cy-26, cx-4, cy-34), fill=OUTLINE, width=3*S)
    # 箱體＋頂蓋＋投票口
    d.rounded_rectangle(R(cx-52, cy-4, cx+52, cy+44), radius=8*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-58, cy-16, cx+58, cy+4), radius=6*S, fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-22, cy-10, cx+22, cy-2), radius=3*S, fill=OUTLINE)
    d.rounded_rectangle(R(cx-44, cy+12, cx-14, cy+19), radius=3*S, fill=tint(theme, 0.45))

def illu_fakevideo(d, R, S, cx, cy, theme):
    """播放畫面＋警告標誌（假訊息／深偽影片）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -44, 3, GOLD), (52, -50, 3, tint(theme, 0.5)),
                         (74, -14, 3, theme)))
    d.ellipse(R(cx-52, cy+48, cx+40, cy+58), fill=tint(theme, 0.18))
    # 螢幕支架
    d.polygon(R(cx-16, cy+18, cx+2, cy+18, cx+8, cy+42, cx-22, cy+42), fill=tint(theme, 0.30),
              outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-34, cy+40, cx+20, cy+48), radius=4*S, fill=theme, outline=OUTLINE, width=3*S)
    # 螢幕外框＋畫面
    d.rounded_rectangle(R(cx-66, cy-42, cx+52, cy+22), radius=9*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-57, cy-33, cx+43, cy+13), radius=4*S, fill=tint(theme, 0.22))
    d.arc(R(cx-62, cy-38, cx-30, cy-6), start=180, end=270, fill='white', width=4*S)
    # 播放鍵
    d.polygon(R(cx-16, cy-22, cx+4, cy-10, cx-16, cy+2), fill=theme, outline=OUTLINE, width=3*S)
    # 焦點細節：金色警告三角＋驚嘆號（右下前景）
    tx, ty = cx+42, cy+16
    d.polygon(R(tx, ty-26, tx+26, ty+18, tx-26, ty+18), fill=GOLD, outline=OUTLINE, width=ow)
    d.line(R(tx, ty-12, tx, ty+4), fill=OUTLINE, width=4*S)
    d.ellipse(R(tx-3, ty+9, tx+3, ty+15), fill=OUTLINE)

def illu_factory(d, R, S, cx, cy, theme):
    """工廠＋上升折線（工業生產／訂單回升）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -40, 3, GOLD), (30, -52, 3, tint(theme, 0.5)),
                         (70, -44, 3, theme)))
    d.ellipse(R(cx-58, cy+44, cx+50, cy+56), fill=tint(theme, 0.18))
    # 煙囪（後層）
    d.rounded_rectangle(R(cx-56, cy-30, cx-38, cy+6), radius=3*S, fill=tint(theme, 0.30),
                        outline=OUTLINE, width=ow)
    # 廠房本體＋鋸齒屋頂
    d.rounded_rectangle(R(cx-64, cy+2, cx+16, cy+42), radius=6*S, fill=theme, outline=OUTLINE, width=ow)
    for i in range(3):
        x0 = cx-58 + i*24
        d.polygon(R(x0, cy+2, x0+11, cy-12, x0+22, cy+2), fill=tint(theme, 0.30),
                  outline=OUTLINE, width=3*S)
    # 廠房窗與門
    for i in range(3):
        wx = cx-54 + i*24
        d.rounded_rectangle(R(wx, cy+12, wx+14, cy+24), radius=2*S, fill='white', outline=OUTLINE, width=2*S)
    d.rounded_rectangle(R(cx-12, cy+28, cx+8, cy+42), radius=2*S, fill=tint(theme, 0.45))
    # 焦點細節：金色上升折線＋箭頭（訂單回升）
    d.line(R(cx+8, cy+4, cx+34, cy-20), fill=GOLD, width=ow+2*S)
    d.line(R(cx+34, cy-20, cx+52, cy-6), fill=GOLD, width=ow+2*S)
    d.line(R(cx+52, cy-6, cx+70, cy-40), fill=GOLD, width=ow+2*S)
    d.polygon(R(cx+70, cy-46, cx+78, cy-24, cx+58, cy-30), fill=GOLD, outline=OUTLINE, width=3*S)

def illu_heatwave(d, R, S, cx, cy, theme):
    """烈日＋溫度計（熱浪／高溫對經濟與健康的衝擊）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -42, 3, GOLD), (4, -50, 3, tint(theme, 0.5)),
                         (72, 26, 3, theme)))
    d.ellipse(R(cx-52, cy+46, cx+52, cy+58), fill=tint(theme, 0.18))
    # 烈日：光芒（先畫）＋日盤
    sx, sy = cx+42, cy-24
    for k in range(8):
        a = math.radians(k*45)
        d.line(R(sx+22*math.cos(a), sy+22*math.sin(a),
                 sx+30*math.cos(a), sy+30*math.sin(a)), fill=GOLD_D, width=4*S)
    d.ellipse(R(sx-20, sy-20, sx+20, sy+20), fill=GOLD, outline=OUTLINE, width=ow)
    d.arc(R(sx-14, sy-14, sx+14, sy+14), start=195, end=250, fill=GOLD_HI, width=4*S)
    # 熱氣波紋（日與溫度計之間）
    for dy in (12, 26):
        d.arc(R(cx+8, cy+dy-8, cx+30, cy+dy+8), start=180, end=360, fill=tint(theme, 0.45), width=3*S)
        d.arc(R(cx+30, cy+dy-8, cx+52, cy+dy+8), start=0, end=180, fill=tint(theme, 0.45), width=3*S)
    # 溫度計：管身＋水銀柱＋球部（焦點細節）
    tx = cx-40
    d.rounded_rectangle(R(tx-11, cy-46, tx+11, cy+18), radius=11*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(tx-4, cy-34, tx+4, cy+18), radius=4*S, fill=theme)
    for dy in (-30, -18, -6):
        d.line(R(tx+4, cy+dy, tx+9, cy+dy), fill=OUTLINE, width=2*S)
    d.ellipse(R(tx-18, cy+14, tx+18, cy+50), fill=theme, outline=OUTLINE, width=ow)
    d.arc(R(tx-12, cy+20, tx+2, cy+34), start=140, end=220, fill='white', width=3*S)

def illu_ailabel(d, R, S, cx, cy, theme):
    """影像框＋AI 標籤徽章（AI 生成內容標示義務）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -40, 3, GOLD), (44, -50, 3, tint(theme, 0.5)),
                         (74, -12, 3, theme)))
    d.ellipse(R(cx-54, cy+46, cx+46, cy+58), fill=tint(theme, 0.18))
    # 影像框＋畫面內容（山景＋小太陽，代表 AI 生成圖像）
    d.rounded_rectangle(R(cx-64, cy-44, cx+36, cy+28), radius=9*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-55, cy-35, cx+27, cy+19), radius=4*S, fill=tint(theme, 0.22))
    d.ellipse(R(cx-45, cy-27, cx-31, cy-13), fill=GOLD, outline=OUTLINE, width=3*S)
    d.polygon(R(cx-52, cy+19, cx-24, cy-10, cx+4, cy+19), fill=theme, outline=OUTLINE, width=3*S)
    d.polygon(R(cx-10, cy+19, cx+10, cy-2, cx+27, cy+19), fill=tint(theme, 0.55), outline=OUTLINE, width=3*S)
    # 焦點細節：金色 AI 標籤徽章（右下前景）
    d.rounded_rectangle(R(cx+8, cy+14, cx+70, cy+48), radius=9*S, fill=GOLD, outline=OUTLINE, width=ow)
    draw_mixed_vcentered(d, R(cx+39, cy+31), 'AI', 26*S, OUTLINE, bold=True, anchor='center')

def illu_piggybank(d, R, S, cx, cy, theme):
    """小豬撲滿＋投入的金幣（兒童儲蓄／長期資本累積）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-68, -40, 3, GOLD), (54, -50, 3, tint(theme, 0.5)),
                         (72, 4, 3, theme)))
    d.ellipse(R(cx-46, cy+46, cx+46, cy+58), fill=tint(theme, 0.18))
    # 金幣（先畫，落在投幣口上方）
    d.ellipse(R(cx-16, cy-40, cx+10, cy-14), fill=GOLD, outline=OUTLINE, width=ow)
    draw_mixed_vcentered(d, R(cx-3, cy-27), '€', 20*S, OUTLINE, bold=True, anchor='center')
    # 豬腳（先畫，藏在豬身之後）
    for lx in (-34, 8):
        d.rounded_rectangle(R(cx+lx, cy+30, cx+lx+16, cy+50), radius=4*S,
                            fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    # 耳朵
    d.polygon(R(cx-18, cy-6, cx-2, cy-6, cx-10, cy-26), fill=theme, outline=OUTLINE, width=3*S)
    # 豬身＋鼻子
    d.ellipse(R(cx-46, cy-8, cx+38, cy+44), fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    d.ellipse(R(cx+28, cy+6, cx+52, cy+28), fill=theme, outline=OUTLINE, width=ow)
    for nx in (36, 44):
        d.ellipse(R(cx+nx, cy+14, cx+nx+4, cy+20), fill=OUTLINE)
    d.ellipse(R(cx+12, cy+2, cx+20, cy+10), fill=OUTLINE)
    # 投幣口（焦點細節）
    d.rounded_rectangle(R(cx-20, cy-4, cx+6, cy+2), radius=3*S, fill=OUTLINE)

def illu_shieldeye(d, R, S, cx, cy, theme):
    """盾牌＋監看之眼（情報機關／國安權限）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-66, -44, 3, GOLD), (52, -50, 3, tint(theme, 0.5)),
                         (70, 6, 3, theme)))
    d.ellipse(R(cx-38, cy+48, cx+38, cy+58), fill=tint(theme, 0.18))
    # 盾牌本體
    d.polygon(R(cx-40, cy-42, cx, cy-52, cx+40, cy-42, cx+40, cy+6, cx, cy+50, cx-40, cy+6),
              fill=tint(theme, 0.28), outline=OUTLINE, width=ow)
    # 金色橫飾帶
    d.rounded_rectangle(R(cx-26, cy-36, cx+26, cy-28), radius=4*S, fill=GOLD, outline=OUTLINE, width=2*S)
    # 監看之眼（焦點細節）
    d.ellipse(R(cx-26, cy-16, cx+26, cy+16), fill='white', outline=OUTLINE, width=ow)
    d.ellipse(R(cx-11, cy-11, cx+11, cy+11), fill=theme, outline=OUTLINE, width=3*S)
    d.ellipse(R(cx-4, cy-4, cx+4, cy+4), fill=OUTLINE)
    d.ellipse(R(cx-8, cy-9, cx-3, cy-4), fill='white')

def illu_agelimit(d, R, S, cx, cy, theme):
    """啤酒杯＋年齡下限徽章（青少年保護／飲酒年齡）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-68, -38, 3, GOLD), (46, -50, 3, tint(theme, 0.5)),
                         (72, -8, 3, theme)))
    d.ellipse(R(cx-44, cy+46, cx+34, cy+58), fill=tint(theme, 0.18))
    # 提把
    d.rounded_rectangle(R(cx+2, cy-12, cx+26, cy+22), radius=12*S, outline=OUTLINE, width=ow)
    # 杯身＋酒液
    d.rounded_rectangle(R(cx-36, cy-28, cx+6, cy+42), radius=7*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-29, cy-6, cx-1, cy+35), radius=4*S, fill=GOLD)
    # 泡沫
    d.rounded_rectangle(R(cx-34, cy-42, cx+4, cy-18), radius=11*S, fill='white', outline=OUTLINE, width=ow)
    # 年齡徽章（焦點細節）
    d.rounded_rectangle(R(cx+14, cy+14, cx+72, cy+48), radius=9*S, fill=theme, outline=OUTLINE, width=ow)
    draw_mixed_vcentered(d, R(cx+43, cy+31), '16', 26*S, 'white', bold=True, anchor='center')

def illu_heathealth(d, R, S, cx, cy, theme):
    """生命徵象監測＋烈日（高溫致死／健康衝擊）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -40, 3, GOLD), (-16, -50, 3, tint(theme, 0.5)),
                         (72, 22, 3, theme)))
    d.ellipse(R(cx-48, cy+48, cx+40, cy+58), fill=tint(theme, 0.18))
    # 烈日（先畫，從螢幕右上探出）
    sx, sy = cx+44, cy-36
    for k in range(8):
        a = math.radians(k*45)
        d.line(R(sx+15*math.cos(a), sy+15*math.sin(a),
                 sx+21*math.cos(a), sy+21*math.sin(a)), fill=GOLD_D, width=4*S)
    d.ellipse(R(sx-14, sy-14, sx+14, sy+14), fill=GOLD, outline=OUTLINE, width=ow)
    # 監測器：支架＋機身＋螢幕
    d.rounded_rectangle(R(cx-13, cy+26, cx+1, cy+42), radius=3*S, fill=tint(theme, 0.30), outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-30, cy+38, cx+18, cy+50), radius=5*S, fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-56, cy-32, cx+38, cy+30), radius=9*S, fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-47, cy-23, cx+29, cy+21), radius=4*S, fill=tint(theme, 0.22))
    # 心電圖折線（焦點細節）
    base = cy + 2
    pts = [(-42, 0), (-30, 0), (-23, -17), (-15, 15), (-7, 0), (24, 0)]
    d.line(R(*[v for (dx, dy) in pts for v in (cx+dx, base+dy)]), fill=theme, width=4*S, joint='curve')

def illu_harvest(d, R, S, cx, cy, theme):
    """麥穗＋乾裂土地（乾旱／收成減產）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -34, 3, GOLD), (6, -50, 3, tint(theme, 0.5)),
                         (70, -14, 3, theme)))
    d.ellipse(R(cx-52, cy+48, cx+52, cy+58), fill=tint(theme, 0.18))
    # 麥穗三株（中間較高）
    for dx, top in ((-34, cy-12), (0, cy-34), (34, cy-12)):
        d.line(R(cx+dx, cy+26, cx+dx, top+8), fill=theme, width=4*S)
        for k in range(4):
            gy = top + k*11
            d.ellipse(R(cx+dx-13, gy, cx+dx-2, gy+10), fill=GOLD, outline=OUTLINE, width=2*S)
            d.ellipse(R(cx+dx+2, gy, cx+dx+13, gy+10), fill=GOLD, outline=OUTLINE, width=2*S)
        d.ellipse(R(cx+dx-5, top-10, cx+dx+5, top+2), fill=GOLD, outline=OUTLINE, width=2*S)
    # 乾裂土地（焦點細節）
    d.rounded_rectangle(R(cx-58, cy+26, cx+58, cy+48), radius=6*S,
                        fill=tint(theme, 0.28), outline=OUTLINE, width=ow)
    for gx, gy in ((-30, 30), (4, 34), (36, 30)):
        d.line(R(cx+gx, cy+gy, cx+gx-5, cy+gy+13), fill=OUTLINE, width=3*S)

def illu_fuelpump(d, R, S, cx, cy, theme):
    """加油機＋加油槍＋上升箭頭（油價／燃油成本）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -46, 3, GOLD), (-40, -56, 3, tint(theme, 0.5)),
                         (72, 30, 3, theme)))
    d.ellipse(R(cx-64, cy+50, cx+8, cy+60), fill=tint(theme, 0.18))
    # 加油機本體：機箱＋頂蓋
    d.rounded_rectangle(R(cx-60, cy-46, cx+2, cy+50), radius=10*S, fill=theme, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-60, cy-46, cx+2, cy-28), radius=10*S, fill=shade(theme, 0.72))
    d.rectangle(R(cx-60, cy-36, cx+2, cy-28), fill=shade(theme, 0.72))
    d.rounded_rectangle(R(cx-60, cy-46, cx+2, cy+50), radius=10*S, outline=OUTLINE, width=ow)
    # 價格螢幕（焦點細節：跳動中的數字）
    d.rounded_rectangle(R(cx-51, cy-20, cx-7, cy+12), radius=5*S, fill='white', outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-45, cy-13, cx-13, cy-6), radius=3*S, fill=GOLD)
    d.rounded_rectangle(R(cx-45, cy-1, cx-25, cy+6), radius=3*S, fill=tint(theme, 0.45))
    # 操作面板
    d.rounded_rectangle(R(cx-51, cy+24, cx-19, cy+31), radius=3*S, fill=tint(theme, 0.45))
    # 軟管＋加油槍（金色，第二焦點）
    d.arc(R(cx-16, cy+6, cx+24, cy+46), start=270, end=360, fill=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx+16, cy+26, cx+58, cy+42), radius=6*S, fill=GOLD, outline=OUTLINE, width=ow)
    d.polygon(R(cx+52, cy+28, cx+70, cy+18, cx+74, cy+25, cx+56, cy+35), fill=GOLD_D, outline=OUTLINE)
    d.rounded_rectangle(R(cx+22, cy+40, cx+34, cy+48), radius=3*S, fill=GOLD_D, outline=OUTLINE, width=3*S)
    # 上升箭頭（漲價）
    d.line(R(cx+18, cy-4, cx+58, cy-44), fill=theme, width=ow+2*S)
    d.polygon(R(cx+40, cy-48, cx+64, cy-52, cx+58, cy-28), fill=theme)

def illu_crane(d, R, S, cx, cy, theme):
    """塔式起重機＋新屋（住宅興建／建照核發）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -28, 3, GOLD), (14, -56, 3, tint(theme, 0.5)),
                         (74, -22, 3, theme)))
    d.ellipse(R(cx-56, cy+48, cx+56, cy+58), fill=tint(theme, 0.18))
    # 塔式起重機（後層）：塔柱＋桁架斜撐
    d.rounded_rectangle(R(cx-58, cy-44, cx-40, cy+46), radius=3*S,
                        fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    for k in range(3):
        yy = cy - 32 + k*26
        d.line(R(cx-58, yy, cx-40, yy+14), fill=OUTLINE, width=2*S)
    # 水平吊臂＋吊索
    d.rounded_rectangle(R(cx-64, cy-58, cx+32, cy-44), radius=4*S,
                        fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    d.line(R(cx+16, cy-44, cx+16, cy-38), fill=OUTLINE, width=3*S)
    # 焦點細節：吊掛中的金色構件（懸在屋脊上方，留出空隙）
    d.rounded_rectangle(R(cx+4, cy-38, cx+28, cy-22), radius=3*S, fill=GOLD,
                        outline=OUTLINE, width=3*S)
    # 新屋：屋頂＋屋身＋門窗
    d.polygon(R(cx-26, cy+6, cx+18, cy-14, cx+62, cy+6), fill=tint(theme, 0.45),
              outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-20, cy+6, cx+56, cy+48), radius=6*S, fill=theme,
                        outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-10, cy+16, cx+8, cy+34), radius=3*S, fill='white',
                        outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx+24, cy+22, cx+46, cy+48), radius=3*S, fill='white',
                        outline=OUTLINE, width=3*S)

def illu_mergebenefits(d, R, S, cx, cy, theme):
    """三張表單匯流成一張（社會給付整併）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-74, -50, 3, GOLD), (-2, -56, 3, tint(theme, 0.5)),
                         (74, -38, 3, theme)))
    d.ellipse(R(cx-56, cy+48, cx+56, cy+58), fill=tint(theme, 0.18))
    # 左側三張分立的小表單（現制三項給付）
    for k in range(3):
        y1 = cy - 44 + k*32
        d.rounded_rectangle(R(cx-72, y1, cx-32, y1+24), radius=4*S, fill='white',
                            outline=OUTLINE, width=3*S)
        d.line(R(cx-65, y1+9, cx-45, y1+9), fill=tint(theme, 0.55), width=3*S)
        d.line(R(cx-65, y1+17, cx-52, y1+17), fill=tint(theme, 0.55), width=3*S)
    # 焦點細節：金色匯流箭頭
    d.line(R(cx-26, cy+4, cx-8, cy+4), fill=GOLD, width=ow+2*S)
    d.polygon(R(cx+8, cy+4, cx-8, cy-5, cx-8, cy+13), fill=GOLD, outline=OUTLINE, width=2*S)
    # 右側整併後的單一給付卡
    d.rounded_rectangle(R(cx+16, cy-38, cx+70, cy+40), radius=7*S, fill=theme,
                        outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx+26, cy-28, cx+54, cy-20), radius=3*S, fill=tint(theme, 0.45))
    for yy in (cy-8, cy+2):
        d.line(R(cx+26, yy, cx+60, yy), fill=tint(theme, 0.45), width=3*S)
    d.ellipse(R(cx+32, cy+12, cx+60, cy+40), fill=GOLD, outline=OUTLINE, width=ow)
    draw_mixed_vcentered(d, R(cx+46, cy+26), '€', 22*S, OUTLINE, bold=True, anchor='center')

def illu_heatlaw(d, R, S, cx, cy, theme):
    """法典＋烈日（高溫防護入憲／氣候調適立法）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -32, 3, GOLD), (-26, -54, 3, tint(theme, 0.5)),
                         (74, 26, 3, theme)))
    d.ellipse(R(cx-54, cy+48, cx+54, cy+58), fill=tint(theme, 0.18))
    # 烈日（後層，自法典右上探出）
    sx, sy = cx+44, cy-30
    for k in range(8):
        a = math.radians(k*45)
        d.line(R(sx+16*math.cos(a), sy+16*math.sin(a),
                 sx+23*math.cos(a), sy+23*math.sin(a)), fill=GOLD_D, width=4*S)
    d.ellipse(R(sx-15, sy-15, sx+15, sy+15), fill=GOLD, outline=OUTLINE, width=ow)
    d.arc(R(sx-10, sy-10, sx+10, sy+10), start=195, end=250, fill=GOLD_HI, width=3*S)
    # 法典：書口（後層）＋封面（前層）
    d.rounded_rectangle(R(cx-50, cy-6, cx+44, cy+46), radius=6*S, fill='white',
                        outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-58, cy-14, cx+36, cy+40), radius=6*S, fill=theme,
                        outline=OUTLINE, width=ow)
    d.line(R(cx-46, cy-14, cx-46, cy+40), fill=OUTLINE, width=3*S)
    # 焦點細節：封面上的金色 § 徽章
    d.rounded_rectangle(R(cx-28, cy, cx+6, cy+32), radius=6*S, fill=GOLD,
                        outline=OUTLINE, width=3*S)
    draw_mixed_vcentered(d, R(cx-11, cy+16), '§', 26*S, OUTLINE, bold=True, anchor='center')

def illu_gavel(d, R, S, cx, cy, theme):
    """法槌＋音板＋可疑包裹（司法判決／破壞行動偵辦）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -40, 3, GOLD), (6, -56, 3, tint(theme, 0.5)),
                         (74, -30, 3, theme)))
    d.ellipse(R(cx-58, cy+48, cx+58, cy+58), fill=tint(theme, 0.18))
    # 槌柄（後層，斜向右上）
    d.polygon(R(cx-17, cy-3, cx+39, cy-39, cx+33, cy-49, cx-23, cy-13),
              fill=tint(theme, 0.45), outline=OUTLINE, width=ow)
    # 槌頭
    d.rounded_rectangle(R(cx-64, cy-32, cx-16, cy+4), radius=8*S, fill=theme,
                        outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-57, cy-25, cx-45, cy-17), radius=3*S, fill=tint(theme, 0.45))
    d.line(R(cx-40, cy-32, cx-40, cy+4), fill=OUTLINE, width=3*S)
    # 音板
    d.rounded_rectangle(R(cx-64, cy+18, cx-8, cy+34), radius=5*S, fill=GOLD,
                        outline=OUTLINE, width=ow)
    # 焦點細節：可疑包裹（膠帶＋金色定位訊號點）
    d.rounded_rectangle(R(cx+16, cy+8, cx+66, cy+50), radius=6*S, fill='white',
                        outline=OUTLINE, width=ow)
    d.line(R(cx+38, cy+8, cx+38, cy+50), fill=tint(theme, 0.55), width=4*S)
    d.line(R(cx+16, cy+24, cx+66, cy+24), fill=tint(theme, 0.55), width=4*S)
    d.ellipse(R(cx+48, cy+30, cx+62, cy+44), fill=GOLD, outline=OUTLINE, width=3*S)

def illu_tornado(d, R, S, cx, cy, theme):
    """雲底垂下的彎曲漏斗＋捲飛的碎片（龍捲風／強風暴）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, 6, 3, GOLD), (-56, 32, 3, tint(theme, 0.5)),
                         (72, -44, 3, theme)))
    d.ellipse(R(cx-42, cy+48, cx+54, cy+58), fill=tint(theme, 0.18))
    # 雲層：寬扁且統一淡色，才不會與漏斗讀成同一塊
    cloud = tint(theme, 0.42)
    for box in ((cx-58, cy-48, cx-20, cy-26), (cx-30, cy-56, cx+16, cy-24),
                (cx+8, cy-46, cx+50, cy-26)):
        d.ellipse(R(*box), fill=cloud, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-56, cy-36, cx+48, cy-27), radius=5*S, fill=cloud)
    d.line(R(cx-52, cy-26, cx+44, cy-26), fill=OUTLINE, width=ow)

    # 漏斗：沿曲線收窄（直錐會讀成甜筒，必須帶彎）
    def axis(t):
        return 18*t*t, 28 - 23*t, -24 + 74*t   # 中心偏移、半寬、y
    left, right = [], []
    for k in range(7):
        ox, hw, yy = axis(k/6)
        left.append((ox-hw, yy))
        right.append((ox+hw, yy))
    funnel = left + right[::-1]
    d.polygon(R(*[v for (dx, dy) in funnel for v in (cx+dx, cy+dy)]),
              fill=theme, outline=OUTLINE, width=ow)
    # 旋轉紋（同色系亮線，跟著漏斗一起偏）
    swirl = tint(theme, 0.55)
    for t, h in ((0.25, 7), (0.5, 6), (0.75, 5)):
        ox, hw, yy = axis(t)
        d.arc(R(cx+ox-hw+4, cy+yy-h, cx+ox+hw-4, cy+yy+h),
              start=200, end=340, fill=swirl, width=3*S)
    # 焦點細節：被捲飛的屋頂碎片
    d.polygon(R(cx+28, cy+10, cx+60, cy+0, cx+64, cy+12, cx+32, cy+22),
              fill=GOLD, outline=OUTLINE, width=3*S)
    d.polygon(R(cx-58, cy+18, cx-32, cy+28, cx-36, cy+38, cx-62, cy+28),
              fill=GOLD_D, outline=OUTLINE, width=3*S)

def illu_wildfire(d, R, S, cx, cy, theme):
    """針葉林＋火焰＋焦土（森林大火）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -44, 3, GOLD), (-2, -56, 3, tint(theme, 0.5)),
                         (72, -30, 3, theme)))
    d.ellipse(R(cx-58, cy+48, cx+58, cy+58), fill=tint(theme, 0.18))
    # 後層針葉樹（剪影，襯在火焰之後）
    for tx, top in ((cx-48, cy-38), (cx+46, cy-28)):
        d.rectangle(R(tx-5, cy+16, tx+5, cy+38), fill=shade(theme, 0.55), outline=OUTLINE, width=3*S)
        for hw, ty in ((22, top+28), (17, top+13), (12, top)):
            d.polygon(R(tx-hw, ty+24, tx+hw, ty+24, tx, ty),
                      fill=tint(theme, 0.35), outline=OUTLINE, width=3*S)
    # 焦土
    d.rounded_rectangle(R(cx-58, cy+36, cx+58, cy+48), radius=6*S,
                        fill=shade(theme, 0.5), outline=OUTLINE, width=ow)
    # 焦點細節：前景火焰（尖頂、波浪腰、收窄的底）
    outer = [(0, -46), (10, -26), (20, -32), (24, -12), (30, 6), (26, 24),
             (12, 38), (-12, 38), (-26, 24), (-30, 6), (-24, -12), (-20, -32), (-10, -26)]
    d.polygon(R(*[v for (dx, dy) in outer for v in (cx+dx, cy+dy)]),
              fill=theme, outline=OUTLINE, width=ow)
    inner = [(0, -14), (9, 4), (13, 16), (8, 32), (-8, 32), (-13, 16), (-9, 4)]
    d.polygon(R(*[v for (dx, dy) in inner for v in (cx+dx, cy+dy)]),
              fill=GOLD, outline=OUTLINE, width=3*S)

def illu_solarpanel(d, R, S, cx, cy, theme):
    """太陽能板＋烈日（光電擴建）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -38, 3, GOLD), (-46, -52, 3, tint(theme, 0.5)),
                         (70, 34, 3, theme)))
    d.ellipse(R(cx-58, cy+46, cx+52, cy+56), fill=tint(theme, 0.18))
    # 烈日（先畫，讓面板疊在前方分層）
    sx, sy = cx+44, cy-30
    for k in range(8):
        a = math.radians(k*45)
        d.line(R(sx+20*math.cos(a), sy+20*math.sin(a),
                 sx+28*math.cos(a), sy+28*math.sin(a)), fill=GOLD_D, width=4*S)
    d.ellipse(R(sx-18, sy-18, sx+18, sy+18), fill=GOLD, outline=OUTLINE, width=ow)
    d.arc(R(sx-12, sy-12, sx+12, sy+12), start=195, end=250, fill=GOLD_HI, width=4*S)
    # 支架與底座
    d.line(R(cx-4, cy+18, cx-4, cy+44), fill=OUTLINE, width=ow+S)
    d.line(R(cx-26, cy+44, cx+18, cy+44), fill=OUTLINE, width=ow)
    # 面板本體
    d.polygon(R(cx-56, cy+22, cx-24, cy-20, cx+52, cy-20, cx+20, cy+22),
              fill=theme, outline=OUTLINE, width=ow)
    # 電池格線
    for k in (1, 2, 3):
        t = k/4
        d.line(R(cx-56+76*t, cy+22, cx-24+76*t, cy-20), fill=tint(theme, 0.5), width=3*S)
    for k in (1, 2):
        t = k/3
        d.line(R(cx-56+32*t, cy+22-42*t, cx+20+32*t, cy+22-42*t), fill=tint(theme, 0.5), width=3*S)
    d.polygon(R(cx-56, cy+22, cx-24, cy-20, cx+52, cy-20, cx+20, cy+22),
              outline=OUTLINE, width=ow)

def illu_evcharge(d, R, S, cx, cy, theme):
    """電動車＋充電樁＋€ 金幣（電動車碳權／THG 配額變現）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-68, -44, 3, GOLD), (-30, -54, 3, tint(theme, 0.5)),
                         (64, -46, 3, GOLD_D)))
    d.ellipse(R(cx-70, cy+46, cx+40, cy+58), fill=tint(theme, 0.18))
    # 充電樁（先畫，讓車身疊在前方分層）
    d.rounded_rectangle(R(cx+38, cy-26, cx+66, cy+40), radius=8*S,
                        fill=GOLD, outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx+45, cy-18, cx+59, cy-4), radius=3*S,
                        fill='white', outline=OUTLINE, width=3*S)
    # 充電線（樁 → 車身充電孔）
    d.arc(R(cx+2, cy-4, cx+52, cy+34), start=270, end=30, fill=OUTLINE, width=4*S)
    # 車身
    d.polygon(R(cx-50, cy-6, cx-36, cy-34, cx+2, cy-34, cx+16, cy-6),
              fill='white', outline=OUTLINE, width=ow)
    d.polygon(R(cx-38, cy-10, cx-30, cy-27, cx-4, cy-27, cx-4, cy-10),
              fill=tint(theme, 0.3))
    d.rounded_rectangle(R(cx-72, cy-8, cx+24, cy+26), radius=13*S,
                        fill=theme, outline=OUTLINE, width=ow)
    # 焦點細節：車門上的閃電
    d.polygon(R(cx-30, cy-2, cx-16, cy-2, cx-22, cy+8, cx-10, cy+8,
                cx-28, cy+22, cx-24, cy+10, cx-34, cy+10),
              fill=GOLD, outline=OUTLINE, width=2*S)
    # 車輪
    for wx in (cx-48, cx+2):
        d.ellipse(R(wx-13, cy+18, wx+13, cy+44), fill=OUTLINE)
        d.ellipse(R(wx-5, cy+26, wx+5, cy+36), fill='white')
    # € 金幣（賣配額換到的錢）
    ex, ey, er = cx-64, cy-30, 18
    d.ellipse(R(ex-er, ey-er, ex+er, ey+er), fill=GOLD, outline=OUTLINE, width=ow)
    d.ellipse(R(ex-er+6, ey-er+6, ex+er-6, ey+er-6), outline=GOLD_D, width=3*S)
    draw_mixed(d, R(ex, ey-13), '\u20ac', 22*S, OUTLINE, bold=True, anchor='center')

ILLUS = dict(podium=illu_podium, flags=illu_flags, coins=illu_coins,
             idcard=illu_idcard, camera=illu_camera, trophy=illu_trophy,
             bankcard=illu_bankcard, checklist=illu_checklist,
             noalcohol=illu_noalcohol, carehand=illu_carehand, contract=illu_contract,
             reichstag=illu_reichstag, candle=illu_candle, briefcase=illu_briefcase,
             drone=illu_drone, lowwater=illu_lowwater, ballotbox=illu_ballotbox,
             fakevideo=illu_fakevideo, factory=illu_factory,
             heatwave=illu_heatwave, ailabel=illu_ailabel,
             piggybank=illu_piggybank, shieldeye=illu_shieldeye,
             agelimit=illu_agelimit, heathealth=illu_heathealth,
             harvest=illu_harvest, fuelpump=illu_fuelpump,
             crane=illu_crane, mergebenefits=illu_mergebenefits,
             heatlaw=illu_heatlaw, gavel=illu_gavel,
             tornado=illu_tornado, wildfire=illu_wildfire,
             solarpanel=illu_solarpanel, evcharge=illu_evcharge)

# ── 版型 ────────────────────────────────────────────────────

def make_card(spec, path, week_label='W?', date_label=''):
    theme = spec['theme']
    img = Image.new('RGB', (W*S, H*S), BG)
    d = ImageDraw.Draw(img)
    def R(*v):
        return [x*S for x in v]

    d.rectangle(R(0, 0, W, 40), fill=theme)
    d.rectangle(R(0, H-12, W, H), fill=theme)
    d.rounded_rectangle(R(36, 60, W-36, 1002), radius=28*S, fill=CARD,
                        outline=BORDER, width=2*S)

    # 插畫淡色圓底（墊在文字層之下、限安全區）
    d.ellipse(R(ILLU_CX-62, ILLU_CY-60, ILLU_CX+62, ILLU_CY+62), fill=tint(theme, 0.10))

    # badges
    bx = 100
    for label, filled in spec['badges']:
        tw = mixed_width(label, 30*S, bold=True)
        bw = tw/S + 52
        y1, y2 = 100, 146
        if filled:
            d.rounded_rectangle(R(bx, y1, bx+bw, y2), radius=23*S, fill=theme)
            draw_mixed_vcentered(d, R(bx+26, (y1+y2)/2), label, 30*S, 'white', bold=True)
        else:
            d.rounded_rectangle(R(bx, y1, bx+bw, y2), radius=23*S, outline=theme, width=3*S)
            draw_mixed_vcentered(d, R(bx+26, (y1+y2)/2), label, 30*S, theme, bold=True)
        bx += bw + 18

    paste_wordmark(img)

    tsize = 62
    while mixed_width(spec['title'], tsize*S, bold=True) > 884*S and tsize > 46:
        tsize -= 2
    draw_mixed(d, R(100, 186 + (62-tsize)//2), spec['title'], tsize*S, TITLE_C, bold=True)
    # 副標同樣做自動縮放，避免長邦名（含德文全名）撐出卡片右緣
    ssize = 36
    while mixed_width(spec['subtitle'], ssize*S) > 884*S and ssize > 27:
        ssize -= 1
    draw_mixed(d, R(100, 266 + (36-ssize)//2), spec['subtitle'], ssize*S, SUB_C)

    # stats 兩格（第三格空間留給插畫）
    for (x1, x2), (num, label) in zip([(100, 380), (400, 680)], spec['stats'][:2]):
        d.rounded_rectangle(R(x1, 316, x2, 436), radius=14*S, fill=STATBG)
        cxx = (x1+x2)/2
        nsize = 48
        while mixed_width(num, nsize*S, bold=True) > (x2-x1-28)*S and nsize > 30:
            nsize -= 2
        draw_mixed(d, R(cxx, 336 + (48-nsize)//2), num, nsize*S, theme, bold=True, anchor='center')
        lsize = 24
        while mixed_width(label, lsize*S) > (x2-x1-20)*S and lsize > 19:
            lsize -= 1
        draw_mixed(d, R(cxx, 394), label, lsize*S, SUB_C, anchor='center')

    # 插畫圖形
    ILLUS[spec['illu']](d, R, S, ILLU_CX, ILLU_CY, theme)

    # bullets
    y = 456
    for header, body in spec['bullets']:
        d.ellipse(R(104, y+12, 122, 30+y), fill=theme)
        draw_mixed(d, R(136, y), header, 33*S, TITLE_C, bold=True)
        y += 42
        for line in wrap_mixed(body, 30*S, 846*S):
            draw_mixed(d, R(136, y), line, 30*S, BODY_C)
            y += 38
        y += 6

    # 底部觀察框
    label, text = spec['takeaway']
    lines = wrap_mixed(text, 30*S, 826*S)
    box_h = 16 + 40 + len(lines)*38 + 14
    y1 = 988 - box_h
    d.rounded_rectangle(R(90, y1, 990, 988), radius=12*S, fill=tint(theme, 0.10))
    d.rounded_rectangle(R(90, y1, 98+8, 988), radius=4*S, fill=theme)
    draw_mixed(d, R(128, y1+16), label, 31*S, theme, bold=True)
    ty = y1 + 58
    for line in lines:
        draw_mixed(d, R(128, ty), line, 30*S, BODY_C)
        ty += 38
    if y > y1 - 6:
        print(f'  ⚠️ overflow: bullets end {y} > takeaway top {y1}  ({path})')

    draw_mixed(d, R(64, 1018), '德國知識小種子', 30*S, SUB_C)
    draw_mixed(d, R(316, 1018), f'{week_label} · {date_label}', 30*S, FOOT_C)
    draw_mixed(d, R(1016, 1018), 'Das deutsche Wissen', 30*S, SUB_C, anchor='right')

    img = img.resize((W, H), Image.LANCZOS)
    img.save(path, 'PNG')
    print('✅', path)

# ════════════════════════════════════════════════════════════
# 每週卡片內容（範本：W29）——之後每週改這一段即可
# ════════════════════════════════════════════════════════════
WEEK = 'W34'
DATE_RANGE = '2026/08/17-08/20'

CARDS = [
 dict(
  theme='#D4740E', badges=[('住房', True), ('生活成本', False)], illu='crane',
  title='建照回升 15.1%，租金照漲 3.2%',
  subtitle='聯邦統計局 8/18 公布：上半年核准 12.63 萬戶，但完工與租金是兩回事',
  stats=[('12.63 萬戶', '上半年核准建照'),
         ('+3.2%', 'Q2 新租約租金年增')],
  bullets=[
   ('核准量連月回升', '聯邦統計局（Destatis）8/18：6 月核准 21,600 戶、年增 13.8%；上半年 126,300 戶、年增 15.1%。'),
   ('回升的還只是紙上數字', '核准不等於動工。德國經濟研究所（IW Köln）估 2026 年完工僅約 21.5 萬戶，遠低於年 40 萬戶目標。'),
   ('租金壓力沒鬆手', '德國抵押債券銀行協會（vdp）：Q2 新租約租金全國年增 3.2%，杜塞道夫 3.6% 最高、柏林僅 0.6%。'),
  ],
  takeaway=('租屋族提醒', '全國缺口估約 100 萬戶，Pestel 研究所更估 140 萬戶。核准領先完工約兩年，短期供給不會鬆。'),
  file='W34_圖卡1_建照回升與租金.png'),
 dict(
  theme='#7C3AED', badges=[('極端天氣', True), ('公共安全', False)], illu='tornado',
  title='龍捲風掃過三邦，1 死多人受傷',
  subtitle='8/19 強雷暴；德國氣象局（DWD）事後確認 Fürstenwalde 為龍捲風',
  stats=[('1 死', '萊茵蘭-普法茲邦'),
         ('約 60 棟', 'Wetzlar 受損房屋')],
  bullets=[
   ('1 死 1 重傷', '萊茵蘭-普法茲邦（Rheinland-Pfalz）Waldorf：兩名女子避雨時被倒下的樹壓中，58 歲身亡、47 歲重傷。'),
   ('兩處確認龍捲風', '布蘭登堡邦（Brandenburg）Fürstenwalde 幼兒園屋頂被掀；黑森邦（Hessen）Wetzlar 約 60 棟房屋受損。'),
   ('為何沒有預警', '德國氣象局（DWD）事前未發警報——龍捲風生成於一朵「不起眼的弱陣雨」，而非典型強雷暴。'),
  ],
  takeaway=('防災提醒', '暴風雨中最危險的往往是樹而不是雨。有頂座椅區、車棚與行道樹下都不算避難處，應進入堅固建築物。'),
  file='W34_圖卡2_龍捲風致死.png'),
 dict(
  theme='#C0392B', badges=[('森林大火', True), ('氣候', False)], illu='wildfire',
  title='許特根森林大火撲滅，燒掉 300 公頃',
  subtitle='北萊茵-西發利亞邦（Nordrhein-Westfalen）有紀錄以來最大森林火災',
  stats=[('約 300 公頃', '過火面積'),
         ('1,800 人', '一度疏散的居民')],
  bullets=[
   ('規模有多大', '8/13 於艾菲爾（Eifel）山區許特根森林（Hürtgenwald）起火，過火約 300 公頃，為該邦 1991 年有統計以來最大。'),
   ('動員與傷情', '8/14 凌晨疏散 Gey 地區約 1,800 名居民、8/15 傍晚才獲准返家；最多動員約 1,800 名救援人員，5 人受傷。'),
   ('為何特別難撲滅', '林地埋有二戰許特根森林戰役遺留彈藥，8/14 夜間曾發生爆炸；地下悶燒火點也讓復燃風險居高不下。'),
  ],
  takeaway=('後續影響', '鎮長 Stephan Cranen 8/20 宣布火勢撲滅。林區樹木受火削弱而不穩，無限期封閉；起火原因仍在調查。'),
  file='W34_圖卡3_許特根森林大火.png'),
 dict(
  theme='#0D9488', badges=[('勞動市場', True), ('經濟', False)], illu='briefcase',
  title='服務業就業自疫情以來首次明顯下滑',
  subtitle='聯邦統計局 8/18：第二季就業 4,570 萬人，較去年同季少 21.2 萬',
  stats=[('4,570 萬人', '第二季就業人數'),
         ('-21.2 萬', '較去年同季')],
  bullets=[
   ('整體走弱', '聯邦統計局（Destatis）初步統計：Q2 就業季調較前一季減 5.3 萬人，年減 21.2 萬人（-0.5%）。'),
   ('服務業是新訊號', '服務業年減 2.7 萬人，為新冠疫情以來首次明顯下降——過去幾年它一直是撐住德國就業的支柱。'),
   ('內部分化明顯', '公共服務、教育與醫療續增 18.7 萬人（+1.5%）；貿易、運輸與餐旅再減 11.5 萬人（-1.1%）。'),
  ],
  takeaway=('求職觀察', '公部門、教育與醫療仍在擴編，餐旅與零售持續縮編；持工作居留者換工作前先看清行業。'),
  file='W34_圖卡4_第二季就業下滑.png'),
 dict(
  theme='#D4740E', badges=[('氣候調適', True), ('修憲', False)], illu='heatlaw',
  title='高溫防護入基本法？民調 65% 贊成',
  subtitle='YouGov 8/19 公布；聯盟黨（CDU/CSU）踩煞車，修憲需三分之二多數',
  stats=[('65%', '贊成修憲的比例'),
         ('近 5 億歐元', '每個高溫日的經濟損失')],
  bullets=[
   ('民調怎麼問', '德通社（dpa）委託 YouGov 於 8/14–8/17 訪問 2,091 人：33% 贊成、32% 偏贊成，反對與偏反對各 11%。'),
   ('要改什麼', '環境部長 Carsten Schneider（SPD）主張把高溫防護寫進基本法、列為聯邦與各邦「共同任務」。'),
   ('卡在哪裡', '聯盟黨團副主席 Günter Krings 稱此舉「對氣候沒有幫助」；德國城市暨鄉鎮聯合會則表態支持。'),
  ],
  takeaway=('政策觀察', '修憲須聯邦議院與聯邦參議院各三分之二多數；走不成，高溫防護的錢仍由各邦與地方自扛。'),
  file='W34_圖卡5_高溫防護入基本法.png'),
 dict(
  theme='#2E8B57', badges=[('能源', True), ('再生能源', False)], illu='solarpanel',
  title='太陽能提前兩年達標：128 GWp',
  subtitle='德國太陽能產業協會（BSW-Solar）8/20 公布；業界同時警告擴建轉折',
  stats=[('128 GWp', '全德光電裝置容量'),
         ('逾 600 萬套', '全德太陽能系統')],
  bullets=[
   ('達成了什麼', '德國太陽能產業協會（BSW-Solar）依聯邦網路局登記資料估算：全德光電容量突破 128 GWp，較法定目標提前兩年。'),
   ('已經佔多少', '2025 年太陽能約佔德國淨發電量五分之一；2024 與 2025 年每年各新增約 17.5 GWp。'),
   ('業界為何仍憂心', '協會警告政策框架調整恐造成「擴建轉折」；2030 年要達 215 GWp，往後每年需新增約 20 GWp。'),
  ],
  takeaway=('數據解讀', '達標提前兩年，但下一階段的年增量要求更高。對自用發電家戶而言，重點將轉向躉購費率與併網規則。'),
  file='W34_圖卡6_太陽能提前達標.png'),
 dict(
  theme='#2563EB', badges=[('社會福利', True), ('家庭', False)], illu='mergebenefits',
  title='三種給付併成一種：ifo 端出改革方案',
  subtitle='勞工福利聯合會（AWO）委託研究 8/19 發表；屬智庫建議，尚未立法',
  stats=[('3 合 1', '基本保障＋住房補貼＋兒童加給'),
         ('32.2 萬人', '估可因此重返就業')],
  bullets=[
   ('要併哪三項', 'ifo 經濟研究所受德國勞工福利聯合會（AWO）委託提案：基本保障、住房補貼與兒童加給併為單一給付。'),
   ('誰受益最多', '單親與多子女家庭。低所得級距家庭可支配所得平均年增 149 €，貧窮風險率自約 16% 再降 0.9 個百分點。'),
   ('為何能拉高就業', '研究主持人 Blömer 指現制多項給付同時遞減、形同高邊際稅率；整併後估多出 18.8 萬個全職工時。'),
  ],
  takeaway=('方案解讀', '代價是國家每年多支出約 54 億歐元。這是智庫方案而非政府草案，仍未進入立法程序。'),
  file='W34_圖卡7_社會給付三合一.png'),
 dict(
  theme='#C0392B', badges=[('司法', True), ('國安', False)], illu='gavel',
  title='俄羅斯破壞案宣判：1 年 3 個月',
  subtitle='斯圖加特高等邦法院 8/18：一人有罪、另兩名被告無罪',
  stats=[('1 年 3 個月', '唯一有罪者刑期'),
         ('2 人', '獲判無罪')],
  bullets=[
   ('判了什麼', '斯圖加特高等邦法院（Oberlandesgericht Stuttgart）8/18 認定 30 歲烏克蘭籍男子為破壞目的從事間諜活動。'),
   ('手法是什麼', '被告自德國寄出兩個內含 GPS 追蹤器的包裹測試貨運路線；下一步是運送途中會自燃的縱火裝置。'),
   ('為何刑度不高', '行動仍停留在準備階段，刑期已由審前羈押折抵、判決後不必再入監；另兩名被告無罪。'),
  ],
  takeaway=('安全觀察', '俄羅斯情報機關近年多以社群媒體招募「拋棄式特務」，用完即切割、成本極低。'),
  file='W34_圖卡8_俄羅斯破壞案宣判.png'),
]

if __name__ == '__main__':
    import os, sys
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        make_card(c, os.path.join(OUT, c['file']), WEEK, DATE_RANGE)
