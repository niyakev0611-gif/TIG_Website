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

ILLUS = dict(podium=illu_podium, flags=illu_flags, coins=illu_coins,
             idcard=illu_idcard, camera=illu_camera, trophy=illu_trophy,
             bankcard=illu_bankcard, checklist=illu_checklist,
             noalcohol=illu_noalcohol, carehand=illu_carehand, contract=illu_contract)

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
    draw_mixed(d, R(100, 266), spec['subtitle'], 36*S, SUB_C)

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
WEEK = 'W30'
DATE_RANGE = '2026/07/20–07/26'

CARDS = [
 dict(
  theme='#2563EB', badges=[('政治', True), ('柏林', False)], illu='podium',
  title='聯盟黨團主席請辭、繼任開跑',
  subtitle='7/18 Spahn 因家庭模式爭議去職；7/29 票選新主席',
  stats=[('7/29', '黨團票選新主席'),
         ('3 人', '繼任熱門人選')],
  bullets=[
   ('請辭導火線', 'Spahn 7/15 公開與伴侶經美國代孕育兒（代孕在德國違法），引發黨內外爭論；總理 Merz 稱其去職「無可避免」。'),
   ('繼任卡位', '總理府部長 Frei 獲 Merz 與 CSU 黨魁 Söder 共同推舉領跑；衛生部長 Warken、內政部長 Dobrindt 亦在名單。'),
   ('連鎖效應', '黨團主席是掌握國會多數、貫徹立法的樞紐；若由現任閣員接任，恐再牽動內閣改組。'),
  ],
  takeaway=('政治觀察', 'Spahn 是聯盟黨連結內閣與國會的橋樑；夏休後改革衝刺期臨陣換將，7/29 人選底定前柏林政壇短暫盤整。'),
  file='W30_圖卡1_聯盟黨團主席請辭.png'),
 dict(
  theme='#D4740E', badges=[('經濟', True), ('薪資', False)], illu='coins',
  title='全職月薪中位數 4,217 €',
  subtitle='聯邦勞工局 7/20 發布 2025 年薪資地圖（Entgeltatlas）',
  stats=[('4,217 €', '全職月薪中位數（稅前）'),
         ('+5.1%', '較 2024 年增 203 €')],
  bullets=[
   ('男女差距收窄', '男性中位數 4,328 €、女性 4,019 €，差距 309 €、年減 37 €；性別差距東部（6%）小於西部（11%）。'),
   ('學歷落差近一倍', '無資格者 3,133 €、有職業資格 4,069 €、大學學歷 6,146 €——文憑差距近一倍。'),
   ('城鄉兩端', '最高在漢堡（Hamburg）、最低在梅克倫堡-西波美拉尼亞（MV）；為全職投保者中位數、非全體平均。'),
  ],
  takeaway=('數據解讀', '中位數＝一半人高於、一半人低於，比平均更貼近多數人；來德工作者可對照職業與邦別評估 offer 高低。'),
  file='W30_圖卡2_全職薪資中位數.png'),
 dict(
  theme='#C0392B', badges=[('民生', True), ('交通', False)], illu='noalcohol',
  title='德鐵 5,400 站全面禁酒',
  subtitle='7/21 宣布；分階段實施至 10 月中旬全國生效',
  stats=[('5,400 站', '全德車站分階段禁酒'),
         ('10 月中', '全國全面上路')],
  bullets=[
   ('導火線', '7/18 一名德鐵（Deutsche Bahn）保全於時速約 120 公里的區間車上墜車重傷，成為全面禁酒的直接推手。'),
   ('分階段上路', '9/1 起柏林中央車站（Berlin Hbf）、基爾（Kiel）、布倫瑞克（Braunschweig）等先行，10 月中旬前全國跟進。'),
   ('例外與罰則', '站內餐飲業者不受限、行李箱內密封攜帶亦可；違規先驅離（Platzverweis），累犯祭出禁足令（Hausverbot）。'),
  ],
  takeaway=('搭車提醒', '常搭火車的你請留意：月台與大廳將陸續禁止飲酒，想小酌得移步站內餐廳；攜帶未開封酒類通關無虞。'),
  file='W30_圖卡3_德鐵全站禁酒.png'),
 dict(
  theme='#0D9488', badges=[('社福', True), ('照護', False)], illu='carehand',
  title='護理保險改革：225 億歐元缺口',
  subtitle='護理重整法（PNOG）草案；內閣 7/29 待審',
  stats=[('225 億歐元', '護理保險年度缺口'),
         ('2027 年', '照護津貼改制上路')],
  bullets=[
   ('錢從哪補', '草案擬調高保費計算上限、無子女者加收 0.1 個百分點；迷你工作（Minijob）納保後每年約挹注 12 億歐元。'),
   ('津貼變革', '2027 年起以「減負預算」（Entlastungsbudget）取代現行照護津貼（Pflegegeld），月額調升、整合分項給付。'),
   ('一再卡關', '內閣原訂 5、6 月審議屢延，最快 7/29 上桌；衛生部長 Warken（CDU）主導，護理界憂新增等待期恐延後給付。'),
  ],
  takeaway=('政策觀察', '護理保險連年入不敷出，改革在加保費與砍給付間拉鋸；家有需照護長輩或從事照護者，2027 年保費與給付都牽動荷包。'),
  file='W30_圖卡4_護理保險改革.png'),
 dict(
  theme='#2E8B57', badges=[('勞動', True), ('薪資', False)], illu='contract',
  title='團體協約覆蓋率僅 49%',
  subtitle='內閣 7/22 通過促進團體協商國家行動計畫',
  stats=[('49%', '德國團體協約覆蓋率'),
         ('80%', 'EU 指令門檻')],
  bullets=[
   ('為何要做', '歐盟最低工資指令規定：協約覆蓋率低於 80% 的成員國須提國家行動計畫；德國僅 49%、遠低於門檻。'),
   ('端了什麼', '含《聯邦協約忠誠法》（5/1 生效、5 萬歐元以上公共標案適用）、工會數位進場權、工會會費可抵稅等。'),
   ('勞方不買單', '勞工部長 Bas（SPD）主導；德國工會聯合會（DGB）批力道不足、「進一步、退兩步」，要求更強制措施。'),
  ],
  takeaway=('勞動觀察', '有沒有團體協約，直接牽動薪資、工時與加班費——這也是「薪資中位數」差距的成因之一；有協約企業通常保障更佳。'),
  file='W30_圖卡5_團體協約行動計畫.png'),
]

if __name__ == '__main__':
    import os, sys
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        make_card(c, os.path.join(OUT, c['file']), WEEK, DATE_RANGE)
