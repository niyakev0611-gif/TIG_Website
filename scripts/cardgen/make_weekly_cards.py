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

def illu_carplant(d, R, S, cx, cy, theme):
    """汽車廠＋下降箭頭（車廠減產／關廠與人力縮編）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -36, 3, GOLD), (-6, -52, 3, tint(theme, 0.5)),
                         (70, -44, 3, theme)))
    d.ellipse(R(cx-58, cy+46, cx+56, cy+58), fill=tint(theme, 0.18))
    # 後層：鋸齒屋頂廠房
    d.rounded_rectangle(R(cx-66, cy-26, cx+18, cy+18), radius=6*S,
                        fill=tint(theme, 0.22), outline=OUTLINE, width=ow)
    for i in range(3):
        x0 = cx-62 + i*26
        d.polygon(R(x0, cy-26, x0+12, cy-40, x0+24, cy-26),
                  fill=tint(theme, 0.38), outline=OUTLINE, width=3*S)
    for i in range(3):
        wx = cx-58 + i*26
        d.rounded_rectangle(R(wx, cy-18, wx+16, cy-4), radius=2*S,
                            fill='white', outline=OUTLINE, width=2*S)
    # 前景：車體側影（單一焦點）
    d.polygon(R(cx-38, cy+20, cx-24, cy+2, cx+2, cy+2, cx+12, cy+20),
              fill=tint(theme, 0.45), outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-56, cy+18, cx+22, cy+42), radius=10*S,
                        fill=theme, outline=OUTLINE, width=ow)
    for wxc in (cx-38, cx+6):
        d.ellipse(R(wxc-11, cy+32, wxc+11, cy+54), fill='white', outline=OUTLINE, width=ow)
        d.ellipse(R(wxc-4, cy+39, wxc+4, cy+47), fill=OUTLINE)
    # 焦點細節：金色下降箭頭（產量與人力雙雙下修）
    d.line(R(cx+42, cy-28, cx+62, cy+12), fill=GOLD, width=ow+2*S)
    d.polygon(R(cx+64, cy+26, cx+48, cy+8, cx+74, cy+2), fill=GOLD, outline=OUTLINE, width=3*S)

def illu_databreach(d, R, S, cx, cy, theme):
    """伺服器機櫃＋斷開的掛鎖（系統遭入侵／資料外流）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -40, 3, theme), (44, -52, 3, GOLD),
                         (74, 14, 3, tint(theme, 0.5))))
    d.ellipse(R(cx-52, cy+46, cx+40, cy+58), fill=tint(theme, 0.18))
    # 伺服器機櫃：外框＋三層機架
    d.rounded_rectangle(R(cx-58, cy-42, cx+18, cy+48), radius=9*S,
                        fill='white', outline=OUTLINE, width=ow)
    for i in range(3):
        y0 = cy-32 + i*26
        d.rounded_rectangle(R(cx-48, y0, cx+8, y0+18), radius=4*S,
                            fill=tint(theme, 0.30), outline=OUTLINE, width=3*S)
        d.line(R(cx-40, y0+9, cx-20, y0+9), fill=OUTLINE, width=3*S)
        d.ellipse(R(cx-2, y0+6, cx+4, y0+12), fill=GOLD if i == 1 else theme)
    # 焦點細節：斷開的掛鎖（前景右側）
    lx, ly = cx+48, cy-12
    d.arc(R(lx-16, ly-30, lx+10, ly-4), start=185, end=350, fill=OUTLINE, width=ow)
    d.rounded_rectangle(R(lx-22, ly-8, lx+22, ly+22), radius=7*S,
                        fill=GOLD, outline=OUTLINE, width=ow)
    d.line(R(lx, ly+1, lx, ly+13), fill=OUTLINE, width=4*S)
    # 外流的資料點（由機櫃流向右下）
    for (dx, dy, r) in ((30, 30, 5), (48, 40, 4), (64, 48, 3)):
        d.ellipse(R(cx+dx-r, cy+dy-r, cx+dx+r, cy+dy+r), fill=theme)

def illu_taxrelief(d, R, S, cx, cy, theme):
    """報稅單＋向下的金色箭頭（所得稅減稅／稅負調降）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -44, 3, GOLD), (-16, -56, 3, tint(theme, 0.5)),
                         (72, -44, 3, theme)))
    d.ellipse(R(cx-52, cy+46, cx+52, cy+58), fill=tint(theme, 0.18))
    # 後層：另一份表單（分層表達厚度）
    d.rounded_rectangle(R(cx-38, cy-40, cx+42, cy+40), radius=7*S,
                        fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    # 前層：報稅單本體
    d.rounded_rectangle(R(cx-52, cy-32, cx+28, cy+48), radius=7*S,
                        fill='white', outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-42, cy-22, cx-4, cy-14), radius=3*S, fill=tint(theme, 0.45))
    for yy in (cy-2, cy+8, cy+18):
        d.line(R(cx-42, yy, cx+16, yy), fill=tint(theme, 0.45), width=3*S)
    d.line(R(cx-42, cy+30, cx-8, cy+30), fill=tint(theme, 0.45), width=3*S)
    # 焦點細節：金色 € 圓章＋向下箭頭（稅負下降）
    ax, ay = cx+44, cy+4
    d.line(R(ax, ay-34, ax, ay+8), fill=GOLD_D, width=ow+S)
    d.polygon(R(ax, ay+24, ax-14, ay+4, ax+14, ay+4), fill=GOLD, outline=OUTLINE, width=3*S)
    d.ellipse(R(ax-18, ay-56, ax+18, ay-20), fill=GOLD, outline=OUTLINE, width=ow)
    draw_mixed_vcentered(d, R(ax, ay-38), '€', 24*S, OUTLINE, bold=True, anchor='center')

def illu_rentburden(d, R, S, cx, cy, theme):
    """小房子被高過屋頂的金幣柱壓住（房租吃掉收入／租金負擔）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -46, 3, theme), (10, -56, 3, GOLD),
                         (74, -50, 3, tint(theme, 0.5))))
    d.ellipse(R(cx-56, cy+46, cx+56, cy+58), fill=tint(theme, 0.18))
    # 左側：住宅（屋頂＋屋身＋門窗）
    d.polygon(R(cx-62, cy+2, cx-24, cy-22, cx+14, cy+2), fill=tint(theme, 0.45),
              outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-56, cy+2, cx+8, cy+48), radius=6*S, fill=theme,
                        outline=OUTLINE, width=ow)
    d.rounded_rectangle(R(cx-46, cy+12, cx-28, cy+30), radius=3*S, fill='white',
                        outline=OUTLINE, width=3*S)
    d.rounded_rectangle(R(cx-14, cy+20, cx+2, cy+48), radius=3*S, fill='white',
                        outline=OUTLINE, width=3*S)
    # 右側：高過屋脊的金幣柱（負擔壓過居住）
    for k in range(5):
        y0 = cy + 40 - k*15
        d.rounded_rectangle(R(cx+24, y0-13, cx+72, y0), radius=6*S,
                            fill=GOLD if k % 2 == 0 else GOLD_D, outline=OUTLINE, width=3*S)
    # 焦點細節：柱頂的 € 硬幣
    d.ellipse(R(cx+30, cy-56, cx+66, cy-20), fill=GOLD, outline=OUTLINE, width=ow)
    draw_mixed_vcentered(d, R(cx+48, cy-38), '€', 24*S, OUTLINE, bold=True, anchor='center')

def illu_pylon(d, R, S, cx, cy, theme):
    """高壓電塔＋警示三角（電網破壞／供電中斷風險）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-72, -46, 3, GOLD), (-30, -56, 3, tint(theme, 0.5)),
                         (76, 34, 3, theme)))
    d.ellipse(R(cx-54, cy+48, cx+54, cy+58), fill=tint(theme, 0.18))
    # 電塔：兩支外張塔腳（底寬頂窄）＋三層橫桁架
    d.line(R(cx-46, cy+48, cx-12, cy-44), fill=OUTLINE, width=ow)
    d.line(R(cx+22, cy+48, cx-12, cy-44), fill=OUTLINE, width=ow)
    d.line(R(cx-12, cy-44, cx-12, cy+48), fill=tint(theme, 0.30), width=3*S)
    for yy, l, r in ((cy+36, -42, 18), (cy+10, -33, 9), (cy-16, -24, 0)):
        d.line(R(cx+l, yy, cx+r, yy), fill=OUTLINE, width=4*S)
    # 塔身斜撐（同色系淺階，分層表達深度）
    for (y0, y1, l0, r0, l1, r1) in ((cy+10, cy+36, -33, 9, -42, 18),
                                     (cy-16, cy+10, -24, 0, -33, 9)):
        d.line(R(cx+l0, y0, cx+r1, y1), fill=tint(theme, 0.55), width=3*S)
        d.line(R(cx+r0, y0, cx+l1, y1), fill=tint(theme, 0.55), width=3*S)
    # 塔頂橫擔＋兩側絕緣礙子（焦點之外的對稱細節）
    d.line(R(cx-40, cy-44, cx+16, cy-44), fill=OUTLINE, width=ow)
    for dx in (-36, 12):
        d.ellipse(R(cx+dx-5, cy-40, cx+dx+5, cy-30), fill=theme, outline=OUTLINE, width=2*S)
    # 焦點細節：金色警示三角（掛在塔身右側）
    tx, ty = cx+50, cy-2
    d.polygon(R(tx, ty-26, tx-24, ty+16, tx+24, ty+16), fill=GOLD,
              outline=OUTLINE, width=ow)
    d.line(R(tx, ty-10, tx, ty+3), fill=OUTLINE, width=4*S)
    d.ellipse(R(tx-3, ty+8, tx+3, ty+14), fill=OUTLINE)

def illu_diploma(d, R, S, cx, cy, theme):
    """證書＋金色印章與勾號（外國專業資格承認）"""
    ow = 5*S
    _dots(d, R, cx, cy, ((-70, -48, 3, theme), (-8, -56, 3, GOLD),
                         (74, -40, 3, tint(theme, 0.5))))
    d.ellipse(R(cx-54, cy+46, cx+54, cy+58), fill=tint(theme, 0.18))
    # 後層：待審的第二份證書
    d.rounded_rectangle(R(cx-30, cy-42, cx+52, cy+30), radius=7*S,
                        fill=tint(theme, 0.30), outline=OUTLINE, width=ow)
    # 前層：證書本體
    d.rounded_rectangle(R(cx-56, cy-32, cx+30, cy+42), radius=7*S,
                        fill='white', outline=OUTLINE, width=ow)
    d.line(R(cx-44, cy-16, cx+18, cy-16), fill=tint(theme, 0.55), width=4*S)
    d.line(R(cx-44, cy-4, cx+4, cy-4), fill=tint(theme, 0.45), width=3*S)
    d.line(R(cx-44, cy+6, cx+12, cy+6), fill=tint(theme, 0.45), width=3*S)
    # 證書上的核可勾號
    d.line(R(cx-40, cy+24, cx-30, cy+34), fill=theme, width=5*S)
    d.line(R(cx-30, cy+34, cx-10, cy+12), fill=theme, width=5*S)
    # 焦點細節：金色鋼印＋緞帶（右下角壓在證書上）
    sx, sy = cx+40, cy+16
    d.polygon(R(sx-16, sy+10, sx-16, sy+42, sx-4, sy+32, sx+8, sy+42, sx+8, sy+10),
              fill=theme, outline=OUTLINE, width=3*S)
    d.ellipse(R(sx-22, sy-18, sx+18, sy+22), fill=GOLD, outline=OUTLINE, width=ow)
    d.ellipse(R(sx-13, sy-9, sx+9, sy+13), fill=GOLD_D)

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
             solarpanel=illu_solarpanel, evcharge=illu_evcharge,
             carplant=illu_carplant, databreach=illu_databreach,
             taxrelief=illu_taxrelief, rentburden=illu_rentburden,
             pylon=illu_pylon, diploma=illu_diploma)

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
    # 自動縮放有下限，縮到底仍過寬就會被卡片右緣裁掉——必須出聲警告
    if mixed_width(spec['title'], tsize*S, bold=True) > 884*S:
        print(f'  ⚠️ title clipped: 縮到 {tsize}px 仍超出 884px，請改短標題  ({path})')
    # 副標同樣做自動縮放，避免長邦名（含德文全名）撐出卡片右緣
    ssize = 36
    while mixed_width(spec['subtitle'], ssize*S) > 884*S and ssize > 27:
        ssize -= 1
    draw_mixed(d, R(100, 266 + (36-ssize)//2), spec['subtitle'], ssize*S, SUB_C)
    if mixed_width(spec['subtitle'], ssize*S) > 884*S:
        print(f'  ⚠️ subtitle clipped: 縮到 {ssize}px 仍超出 884px，請改短副標  ({path})')

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

# ── 純圖表版型（成對長條圖，兩屆選舉比較）──────────────────
# 配色以 dataviz 六項檢查驗過：橙 #D4740E（舊）× 藍 #2563EB（新）
# 於淺色底通過亮度帶、彩度、色盲分離（protan ΔE 32.0）、一般視覺與對比度。
SERIES_OLD, SERIES_NEW = '#D4740E', '#2563EB'
GRID_C = '#E3DFD8'

def make_chart_card(spec, path, week_label='W?', date_label=''):
    """成對水平長條圖：同一組類別的兩期數值比較（無 bullets／stats／觀察框）"""
    theme = spec['theme']
    img = Image.new('RGB', (W*S, H*S), BG)
    d = ImageDraw.Draw(img)
    def R(*v):
        return [x*S for x in v]

    d.rectangle(R(0, 0, W, 40), fill=theme)
    d.rectangle(R(0, H-12, W, H), fill=theme)
    d.rounded_rectangle(R(36, 60, W-36, 1002), radius=28*S, fill=CARD,
                        outline=BORDER, width=2*S)

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

    tsize = 56
    while mixed_width(spec['title'], tsize*S, bold=True) > 884*S and tsize > 42:
        tsize -= 2
    draw_mixed(d, R(100, 186 + (56-tsize)//2), spec['title'], tsize*S, TITLE_C, bold=True)
    if mixed_width(spec['title'], tsize*S, bold=True) > 884*S:
        print(f'  ⚠️ title clipped: 縮到 {tsize}px 仍超出 884px，請改短標題  ({path})')
    ssize = 32
    while mixed_width(spec['subtitle'], ssize*S) > 884*S and ssize > 25:
        ssize -= 1
    draw_mixed(d, R(100, 258 + (32-ssize)//2), spec['subtitle'], ssize*S, SUB_C)
    if mixed_width(spec['subtitle'], ssize*S) > 884*S:
        print(f'  ⚠️ subtitle clipped: 縮到 {ssize}px 仍超出 884px，請改短副標  ({path})')

    # 圖例（兩組數列一律附圖例，識別不靠顏色單一管道）
    lx, ly = 100, 312
    for col, name in ((SERIES_OLD, spec['label_old']), (SERIES_NEW, spec['label_new'])):
        d.rounded_rectangle(R(lx, ly+4, lx+26, ly+22), radius=4*S, fill=col)
        draw_mixed(d, R(lx+36, ly), name, 27*S, BODY_C, bold=True)
        lx += 36 + mixed_width(name, 27*S, bold=True)/S + 34

    # 繪圖區
    X0, X1 = 258, 780          # 長條起點與滿刻度（右側留給變化欄）
    VMAX = spec.get('vmax', 46)
    rows = spec['rows']
    top, row_h = 356, 74
    def vx(v):
        return X0 + (X1 - X0) * v / VMAX

    # recessive 格線（畫在長條之下）
    for g in range(0, int(VMAX)+1, 10):
        gx = vx(g)
        d.line(R(gx, top-10, gx, top + len(rows)*row_h - 12), fill=GRID_C, width=2*S)
        draw_mixed(d, R(gx, top + len(rows)*row_h - 6), f'{g}%', 22*S, FOOT_C, anchor='center')

    for i, (name, v_old, v_new, delta) in enumerate(rows):
        cy = top + i*row_h
        draw_mixed(d, R(100, cy + 18), name, 30*S, TITLE_C, bold=True)
        # 上：舊屆；下：新屆。兩條之間留 4px 底色間隙
        for k, (v, col) in enumerate(((v_old, SERIES_OLD), (v_new, SERIES_NEW))):
            by = cy + 8 + k*26
            if v is None:                       # 該屆尚未成立 → 不畫長條，只標記
                draw_mixed(d, R(X0 + 6, by - 3), '—', 26*S, FOOT_C)
                continue
            d.rounded_rectangle(R(X0, by, max(vx(v), X0 + 8), by + 22), radius=4*S, fill=col)
            draw_mixed(d, R(max(vx(v), X0 + 8) + 12, by - 3), f'{v:.1f}%', 26*S, BODY_C, bold=True)
        # 變化量（文字一律用墨色，不套數列色）
        draw_mixed(d, R(990, cy + 18), delta, 29*S, BODY_C, bold=True, anchor='right')

    # 圖表註腳
    ny = top + len(rows)*row_h + 30
    for line in spec.get('notes', ()):
        draw_mixed(d, R(100, ny), line, 24*S, SUB_C)
        ny += 32

    draw_mixed(d, R(64, 1018), '德國知識小種子', 30*S, SUB_C)
    draw_mixed(d, R(316, 1018), f'{week_label} · {date_label}', 30*S, FOOT_C)
    draw_mixed(d, R(1016, 1018), 'Das deutsche Wissen', 30*S, SUB_C, anchor='right')

    if ny > 996:
        print(f'  ⚠️ overflow: 註腳結束 {ny} 已超出卡片下緣  ({path})')

    img = img.resize((W, H), Image.LANCZOS)
    img.save(path, 'PNG')
    print('✅', path)

# ════════════════════════════════════════════════════════════
# 每週卡片內容（範本：W29）——之後每週改這一段即可
# ════════════════════════════════════════════════════════════
WEEK = 'W36'
DATE_RANGE = '2026/08/31-09/06'

CARDS = [
 dict(
  theme='#2563EB', badges=[('邦選舉', True), ('薩克森-安哈特邦', False)], illu='ballotbox',
  title='薩克森-安哈特邦：AfD 44%，CDU 腰斬',
  subtitle='薩克森-安哈特邦（Sachsen-Anhalt）9/6 開票，投票率飆至約 77%',
  stats=[('44%', 'AfD 得票（2021 年 20.8%）'),
         ('17.5%', 'CDU 得票（2021 年 37.1%）')],
  bullets=[
   ('開出什麼結果', '21 時 12 分推估值：AfD 44%、CDU 17.5%、綠黨與 SPD 各 9.0%、左翼黨 8.9%、BSW 5.0%，FDP 以 2.4% 跌出邦議會。'),
   ('投票率暴增', '約 77%，遠高於 2021 年的 60.3%。AfD 較上屆增逾 23 個百分點，CDU 失血近 20 個百分點，但 AfD 仍未過半。'),
   ('各方怎麼說', 'AfD 的 Chrupalla：「Merz 想把我們減半，我們現在把 CDU 減半了」；Weidel 稱「歷史性結果」並主張執政委託。'),
  ],
  takeaway=('選後觀察', 'CDU 的不相容決議同時排除 AfD 與左翼黨，組閣難度極高。本月另有 9/20 柏林邦（Berlin）議會選舉。'),
  file='W36_圖卡1_薩克森安哈特邦選舉結果.png'),
 dict(
  kind='chart', theme='#2563EB', badges=[('選舉數據', True), ('薩克森-安哈特邦', False)],
  title='兩屆對照：AfD 翻倍，CDU 掉了一半以上',
  subtitle='薩克森-安哈特邦（Sachsen-Anhalt）邦議會選舉第二票得票率，2021 vs 2026',
  label_old='2021 年', label_new='2026 年', vmax=46,
  rows=[
   ('AfD',   20.8, 44.0, '+23.2'),
   ('CDU',   37.1, 17.5, '-19.6'),
   ('綠黨',   5.9,  9.0, '+3.1'),
   ('SPD',    8.4,  9.0, '+0.6'),
   ('左翼黨', 11.0,  8.9, '-2.1'),
   ('BSW',   None,  5.0, '首次參選'),
   ('FDP',    6.4,  2.4, '-4.0'),
  ],
  notes=[
   '2026 年為 9/6 開票夜 21 時 12 分推估值，非最終官方結果；2021 年為官方最終結果。',
   'BSW（Bündnis Sahra Wagenknecht）於 2021 年尚未成立。投票率自 60.3% 升至約 77%。',
  ],
  file='W36_圖卡2_兩屆選舉得票對照.png'),
 dict(
  theme='#2E8B57', badges=[('稅制', True), ('家庭', False)], illu='taxrelief',
  title='內閣通過所得稅改革：一年減稅百億歐元',
  subtitle='9/2 通過《2027 所得稅改革法》草案，2027、2028 分兩階段生效',
  stats=[('100 億歐元', '2028 年起全年減稅規模'),
         ('逾 600 €', '雙薪雙孩 6 萬歐元家庭年省')],
  bullets=[
   ('基本免稅額往上調', '基本免稅額（Grundfreibetrag）2027 年升至 12,564 €、2028 年再升至 12,900 €，等於兩年各多出 216 € 與 336 € 免稅。'),
   ('孩子的部分加最多', '兒童津貼（Kindergeld）2027 年起每月 267 €、2028 年再加 5 € 至 272 €；兒童免稅額每名子女自 9,756 € 調高至 10,056 €。'),
   ('高所得端反向加稅', '45% 稅率的起徵點自 277,826 € 下修至 250,000 €；28 萬歐元以上另立 47% 新稅級，SPD 稱之為「超級富人稅」。'),
  ],
  takeaway=('稅務提醒', '42% 稅率起點自 69,879 € 微調至 70,600 €，1.78 萬至 7.06 萬歐元區間的稅率曲線變平緩。法案仍待國會審議。'),
  file='W36_圖卡3_所得稅改革內閣通過.png'),
 dict(
  theme='#C0392B', badges=[('居住', True), ('租金', False)], illu='rentburden',
  title='租金報告：每兩名租客就有一人怕找不到房',
  subtitle='德國租客協會 9/1 發表《2026 租金報告》，全德缺 140 萬戶住宅',
  stats=[('50%', '怕找不到負擔得起的房'),
         ('140 萬戶', '全德住宅短缺數')],
  bullets=[
   ('租客在怕什麼', '50% 受訪租客擔心一旦得搬家就找不到負擔得起的房；29% 擔心未來付不出房租，四分之一為了付房租而省吃。'),
   ('住房成本還在漲', '58% 表示過去 12 個月房租或雜費（Nebenkosten）變貴；2025 年有 11.2% 的人把逾四成可支配所得花在居住上。'),
   ('雙方開的藥方相反', '租客協會主席 Melanie Weber-Moritz 要求管制租金、擴建社會住宅；房東協會 Haus & Grund 反批「藥方一直開錯」。'),
  ],
  takeaway=('租屋提醒', '貧窮人口中有 35% 的居住支出超過所得四成，報告示警住房危機正轉為社會國危機。'),
  file='W36_圖卡4_租金報告缺140萬戶.png'),
 dict(
  theme='#D4740E', badges=[('通膨', True), ('能源', False)], illu='coins',
  title='八月通膨升到 2.9%，能源獨漲一成',
  subtitle='聯邦統計局 8/29 速報：能源年增 10.5%，為本輪物價的主要推手',
  stats=[('2.9%', '8 月消費者物價年增率'),
         ('+10.5%', '能源價格年增幅')],
  bullets=[
   ('哪些漲、哪些沒漲', '能源年增 10.5%（7 月 8.3%、6 月 3.4%，逐月加速）；服務年增 2.8%；食品幾乎持平，只年增 0.1%。'),
   ('為什麼是能源', '6/30 燃料稅減免退場的效果整月反映在油價上，加上俄國煉油產能受創推高精煉產品價格，能源成了唯一的加速項。'),
   ('核心通膨仍偏高', '扣除食品與能源的核心通膨為 2.4%，高於歐洲央行 2% 的目標，代表漲價壓力並非只來自能源這一項。'),
  ],
  takeaway=('數據解讀', '這是速報值，終值 9/10 公布。物價月增 0.2%，短期回落空間有限，暖氣季前宜先比價電力與天然氣合約。'),
  file='W36_圖卡5_八月通膨與能源.png'),
 dict(
  theme='#7C3AED', badges=[('關鍵基礎設施', True), ('三邦連環破壞', False)], illu='pylon',
  title='電網連環破壞：五個發電機組一度離線',
  subtitle='9/1 起布蘭登堡邦（Brandenburg）等三邦遇襲，嫌犯全歐通緝中',
  stats=[('逾 20 具', '射向高壓線的自製飛行物'),
         ('5 個', '一度離線的褐煤機組')],
  bullets=[
   ('哪裡被攻擊', '9/1 晚間布蘭登堡邦 Turnow-Preilack 與北萊茵-西發利亞邦（Nordrhein-Westfalen）Bergheim 兩處同步遇襲。'),
   ('手法是什麼', '以自製火箭把銅線等導電材料射上高壓線製造短路；Bergheim 一案使 Niederaußem 與 Neurath 五個褐煤機組一度離線。'),
   ('查到誰了', '兩封認犯信寄抵多家媒體且被認定為真；嫌疑人是 Gevelsberg 一名 48 歲男子，目前仍在逃。'),
  ],
  takeaway=('觀察重點', '認犯信稱化石燃料發電是犯罪；聯邦內政部長 Dobrindt 將本案定性為單一行為人的「氣候恐怖主義」。'),
  file='W36_圖卡6_電網連環破壞.png'),
 dict(
  theme='#0D9488', badges=[('工作', True), ('外國專業人員', False)], illu='diploma',
  title='外國專業資格承認創新高，等待仍以年計',
  subtitle='聯邦統計局：2025 年 86,600 件獲承認，年增 10%，但成長已明顯放緩',
  stats=[('86,600 件', '2025 年獲承認的資格'),
         ('32,000 件', '護理師，居所有職類之冠')],
  bullets=[
   ('數字創下新高', '2025 年共 86,600 件外國專業資格獲正面承認，較 2024 年的 79,100 件成長近 10%，為統計以來最多。'),
   ('成長明顯踩了煞車', '前兩年成長率分別是 2024 年的 21% 與 2023 年的 25%；2025 年共處理 102,900 件程序，其中 76,200 件為當年新申請。'),
   ('哪些職類最多', '護理師（Pflegefachfrau/-mann）以 32,000 件遙遙領先，其次為醫師 13,900 件與工程師 4,600 件。'),
  ],
  takeaway=('求職提醒', '受訪當事人指程序動輒等上兩年。申請前先確認職類屬管制或非管制，並備妥翻譯與公證文件以免補件重來。'),
  file='W36_圖卡7_外國資格承認創新高.png'),
]

# ── 邦名德文全名檢查 ────────────────────────────────────────
# CLAUDE.md 鐵則：提到聯邦邦一律寫「◯◯邦」並附德文全名，不可只給簡寫或只有中文。
# 目測會漏（W36 第 6 張就漏了），故在產圖時自動掃描每張卡的全部文字。
STATES = {
    '梅克倫堡-佛波門': 'Mecklenburg-Vorpommern',
    '北萊茵-西發利亞': 'Nordrhein-Westfalen',
    '什勒斯維希-霍爾斯坦': 'Schleswig-Holstein',
    '下薩克森': 'Niedersachsen',
    '巴登-符騰堡': 'Baden-Württemberg',
    '萊茵蘭-普法茲': 'Rheinland-Pfalz',
    '薩克森-安哈特': 'Sachsen-Anhalt',
    '圖林根': 'Thüringen',
    '巴伐利亞': 'Bayern',
    '黑森': 'Hessen',
    '薩爾蘭': 'Saarland',
    '布蘭登堡': 'Brandenburg',
    '不來梅': 'Bremen',
    '漢堡': 'Hamburg',
    '柏林': 'Berlin',
    '薩克森': 'Sachsen',          # 需排在「下薩克森」「薩克森-安哈特」之後比對
}

def check_states(spec):
    """卡片提到某邦卻沒附德文全名時出聲警告"""
    blob = ' '.join([spec['title'], spec['subtitle'],
                     ' '.join(l for b in spec['badges'] for l in (b[0],)),
                     ' '.join(h + b for h, b in spec.get('bullets', ())),
                     ' '.join(spec.get('takeaway', ())),
                     ' '.join(str(v) for r in spec.get('rows', ()) for v in r[:1]),
                     ' '.join(spec.get('notes', ()))])
    seen = ''
    for zh, de in STATES.items():
        # 先扣掉已比對過的長邦名，避免「薩克森」誤命中「下薩克森」「薩克森-安哈特」
        probe = blob
        for longer in seen.split('|'):
            if longer:
                probe = probe.replace(longer, '')
        if (zh + '邦') in probe and de not in blob:
            print(f"  ⚠️ 邦名缺德文: 提到「{zh}邦」但全卡未出現 {de}  ({spec['file']})")
        seen += '|' + zh


_notdef_cache = {}
def _notdef(font):
    """該字型的 .notdef（豆腐框）像素樣本"""
    key = id(font)
    if key not in _notdef_cache:
        _notdef_cache[key] = bytes(font.getmask('\uffff'))
    return _notdef_cache[key]

def check_glyphs(spec):
    """掃描卡片所有文字，揪出會渲染成 .notdef 豆腐框的缺字

    踩過的雷：U+2212 MINUS SIGN「−」在本機 Noto Sans 沒有字符，
    但 getmask() 仍回傳豆腐框的尺寸，光看寬度看不出問題，圖上才會露餡。
    這裡以「已知一定缺字」的字元取得豆腐框尺寸當基準來比對。
    """
    texts = [spec['title'], spec['subtitle']]
    texts += [b[0] for b in spec['badges']]
    texts += [h for h, _ in spec.get('bullets', ())] + [b for _, b in spec.get('bullets', ())]
    texts += list(spec.get('takeaway', ())) + list(spec.get('notes', ()))
    texts += [str(v) for r in spec.get('rows', ()) for v in r]
    texts += [spec.get('label_old', ''), spec.get('label_new', '')]
    texts += [n for n, _ in spec.get('stats', ())] + [l for _, l in spec.get('stats', ())]

    bad = set()
    for t in texts:
        for ch in set(t):
            if ch.isspace():
                continue
            f = cjk(40, True) if is_cjk_char(ch) else lat(40, True)
            # 只比尺寸會誤判：CJK 字符本身就是全形方塊，與豆腐框同尺寸。
            # 必須比對實際像素。
            if bytes(f.getmask(ch)) == _notdef(f):
                bad.add(ch)
    for ch in sorted(bad):
        print(f"  ⚠️ 缺字: 「{ch}」(U+{ord(ch):04X}) 在字型中不存在，會印成豆腐框  ({spec['file']})")

if __name__ == '__main__':
    import os, sys
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        check_states(c)
        check_glyphs(c)
        render = make_chart_card if c.get('kind') == 'chart' else make_card
        render(c, os.path.join(OUT, c['file']), WEEK, DATE_RANGE)
