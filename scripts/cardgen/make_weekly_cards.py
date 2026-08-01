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

ILLUS = dict(podium=illu_podium, flags=illu_flags, coins=illu_coins,
             idcard=illu_idcard, camera=illu_camera, trophy=illu_trophy,
             bankcard=illu_bankcard, checklist=illu_checklist,
             noalcohol=illu_noalcohol, carehand=illu_carehand, contract=illu_contract,
             reichstag=illu_reichstag, candle=illu_candle, briefcase=illu_briefcase)

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
WEEK = 'W31'
DATE_RANGE = '2026/07/27–08/02'

CARDS = [
 dict(
  theme='#2563EB', badges=[('政治', True), ('柏林', False)], illu='reichstag',
  title='內閣改組：Frei 接掌聯盟黨團',
  subtitle='7/29 當選黨團主席；總理府、衛生、交通三部會換將',
  stats=[('91.9%', 'Frei 得票率（170/185 票）'),
         ('3 部會', '總理府・衛生・交通換將')],
  bullets=[
   ('黨團補選', 'Frei 7/29 以 91.9% 高票當選聯盟黨（CDU/CSU）黨團主席，接替因代孕爭議請辭的 Spahn，黨政樞紐重新到位。'),
   ('內閣三換', 'Warken 轉掌總理府、黨秘書長 Linnemann 接衛生部、Bilger 接交通部；Schnieder 數日拉鋸後主動求去。'),
   ('過程失分', 'Merz 屬意的交通人選 Güntzler 自認不具專業婉拒；新閣員 9/9 國會復會才宣誓，改組被批演成「溝通災難」。'),
  ],
  takeaway=('政治觀察', 'AfD 黨魁 Weidel 譏改組是「難堪方案大集合」；Linnemann 無衛生政策歷練直接掌部，專業性質疑恐伴隨上任。'),
  file='W31_圖卡1_內閣改組.png'),
 dict(
  theme='#C0392B', badges=[('治安', True), ('柏林', False)], illu='candle',
  title='柏林 CSD 遇襲：1 死 31 傷',
  subtitle='7/25 遊行遭車輛與砍刀攻擊；安全政策辯論升溫',
  stats=[('1 死 31 傷', '7/25 CSD 攻擊事件'),
         ('16 歲起', '嫌犯遭安全單位列管')],
  bullets=[
   ('案發經過', '21 歲男子駕小巴在蒂爾加滕（Tiergarten）衝撞 CSD 遊行人群、再持砍刀攻擊；翌日圍捕時拒捕遭警方擊斃。'),
   ('列管卻未攔下', '嫌犯為列管伊斯蘭主義危險分子（Gefährder），今年 5 月才因預備恐攻罪判緩刑釋放，「為何在外」成質問焦點。'),
   ('政策急轉', '內政部長 Dobrindt 提三點方案：危險分子電子監控常態化、預防性拘留全國一致入法、成年危險分子不適用少年刑法。'),
  ],
  takeaway=('後續觀察', '情報機關擴權與安全法案 8 月排入內閣；電子腳鐐與預防性拘留涉基本權限制，立法與違憲審查攻防勢將展開。'),
  file='W31_圖卡2_柏林CSD遇襲.png'),
 dict(
  theme='#2E8B57', badges=[('經濟', True), ('數據', False)], illu='coins',
  title='Q2 成長 0.2%、通膨回升 2.8%',
  subtitle='Destatis 7/30 公布；能源推升通膨至四月以來新高',
  stats=[('+0.2%', 'Q2 GDP 季增（優於預期）'),
         ('2.8%', '七月通膨（六月 2.3%）')],
  bullets=[
   ('連兩季正成長', 'Q2 GDP 季增 0.2%、優於市場預期的 0.1%，年增 0.9%；Q1 同步上修至 +0.4%，復甦動能比預想強。'),
   ('通膨反彈', '七月通膨 2.8% 創四月以來新高：中東緊張推升油價，能源年漲幅自 3.4% 跳升至 8.3% 是最大推手。'),
   ('展望上修', 'Commerzbank 將 2026 全年成長預測自 0.6% 上調至 1.0%，直言「德國經濟的復甦比先前以為的更明顯」。'),
  ],
  takeaway=('數據解讀', '成長回穩、通膨卻重新逼近 3%，呼應 ECB 六月升息的判斷；油價若居高不下，秋冬能源帳單宜預留緩衝。'),
  file='W31_圖卡3_Q2經濟與通膨.png'),
 dict(
  theme='#D4740E', badges=[('勞動', True), ('就業', False)], illu='briefcase',
  title='失業人數重返 300 萬',
  subtitle='聯邦勞工局 7/31 公布七月就業市場數據',
  stats=[('300.7 萬', '七月失業人數'),
         ('6.4%', '失業率（月增 0.2 個百分點）')],
  bullets=[
   ('季節性攀升', '七月失業較六月增 7.1 萬人，主因暑休與畢業季例行波動；經季節調整僅增 6 千人、失業率 6.4%。'),
   ('年比仍偏弱', '失業人數較去年同期多 2.8 萬；勞工局理事 Terzenbach 直言，就業市場「延續近幾個月的疲弱走勢」。'),
   ('與景氣背離', '同週公布的 Q2 GDP 優於預期，但企業徵才仍觀望——就業向來落後景氣，招聘回暖通常再晚兩、三季。'),
  ],
  takeaway=('求職提醒', '職缺整體偏緊，IT、護理與技術職種仍缺工；求職與轉職者可鎖定缺工職業，並留意失業保險與試用期權益。'),
  file='W31_圖卡4_失業重返300萬.png'),
 dict(
  theme='#0D9488', badges=[('民生', True), ('新制', False)], illu='checklist',
  title='八月新制：課後照顧入法',
  subtitle='小一課後照顧成法定權利；AI 內容 8/2 起強制標示',
  stats=[('8 小時', '小一每日課後照顧保障'),
         ('8/2', 'AI 內容標示義務生效')],
  bullets=[
   ('課後照顧', '8/1 起小一新生依法享每週 5 天、每日 8 小時課後照顧（Ganztagsbetreuung），逐年擴及 2029/30 全體小學生。'),
   ('AI 標示', 'EU AI 法新階段 8/2 生效：AI 生成影音圖文須明確標示，違者最高罰 1,500 萬歐元或全球年營收 3%。'),
   ('交通能源', '德鐵 BahnBonus 改動態點數，早鳥兌換 750 點起、彈性票調漲 25%；新太陽能躉購費率例行調降 1%。'),
  ],
  takeaway=('民生提醒', '家有學童可向學校或青少年局申請課後名額；經營內容、電商或使用聊天機器人者，檢查 AI 標示義務是否已合規。'),
  file='W31_圖卡5_八月新制.png'),
]

if __name__ == '__main__':
    import os, sys
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        make_card(c, os.path.join(OUT, c['file']), WEEK, DATE_RANGE)
