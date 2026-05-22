"""Weekly newsletter cards for 德國知識小種子, Week 21 (May 18-22, 2026)."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = "/home/user/TIG_Website/sessions/2026-W21/mnt/Claude"

CJK_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
LATIN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG = "#F8F6F2"
CARD = "#FFFFFF"
BORDER = "#E8E4DE"
TEXT_DARK = "#222222"
TEXT_GREY = "#555555"
TEXT_LIGHT = "#888888"

PALETTE = {
    "green":  "#2E8B57",
    "red":    "#C0392B",
    "orange": "#D4740E",
    "blue":   "#2563EB",
    "purple": "#7C3AED",
    "teal":   "#0D9488",
}

W, H = 1080, 1080


def is_cjk(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    # CJK Unified, Compat, Extension A, Hiragana/Katakana, Hangul, Fullwidth forms, CJK punct
    return (
        0x3000 <= o <= 0x303F or
        0x3040 <= o <= 0x30FF or
        0x3400 <= o <= 0x4DBF or
        0x4E00 <= o <= 0x9FFF or
        0xAC00 <= o <= 0xD7AF or
        0xF900 <= o <= 0xFAFF or
        0xFF00 <= o <= 0xFFEF
    )


def load_fonts(size):
    cjk = ImageFont.truetype(CJK_FONT, size)
    lat = ImageFont.truetype(LATIN_FONT, size)
    return cjk, lat


def measure_run(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def split_runs(text):
    """Split text into runs of [(is_cjk, substring)] for font switching."""
    runs = []
    if not text:
        return runs
    cur = text[0]
    cur_is_cjk = is_cjk(cur)
    for ch in text[1:]:
        ch_is_cjk = is_cjk(ch)
        if ch_is_cjk == cur_is_cjk:
            cur += ch
        else:
            runs.append((cur_is_cjk, cur))
            cur = ch
            cur_is_cjk = ch_is_cjk
    runs.append((cur_is_cjk, cur))
    return runs


def draw_mixed(draw, xy, text, size, color, anchor="left"):
    """Draw mixed CJK/Latin text. anchor: 'left', 'center', 'right'."""
    cjk_font, lat_font = load_fonts(size)
    runs = split_runs(text)
    total_w = sum(measure_run(draw, t, cjk_font if c else lat_font) for c, t in runs)

    x, y = xy
    if anchor == "center":
        x -= total_w // 2
    elif anchor == "right":
        x -= total_w

    for is_cjk_run, t in runs:
        f = cjk_font if is_cjk_run else lat_font
        draw.text((x, y), t, font=f, fill=color)
        x += measure_run(draw, t, f)
    return total_w


def measure_mixed(draw, text, size):
    cjk_font, lat_font = load_fonts(size)
    runs = split_runs(text)
    return sum(measure_run(draw, t, cjk_font if c else lat_font) for c, t in runs)


def wrap_mixed(draw, text, size, max_width):
    """Word-wrap mixed CJK/Latin text to a pixel width. CJK breaks per-char;
    Latin breaks on spaces."""
    cjk_font, lat_font = load_fonts(size)

    # Tokenize: CJK chars are individual tokens; Latin words+spaces stick together
    tokens = []
    buf = ""
    buf_is_cjk = None
    for ch in text:
        c = is_cjk(ch)
        if c:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
            buf_is_cjk = None
        else:
            if ch == " " and buf:
                tokens.append(buf)
                tokens.append(" ")
                buf = ""
            else:
                buf += ch
    if buf:
        tokens.append(buf)

    lines = []
    line = ""
    for tok in tokens:
        candidate = line + tok
        if measure_mixed(draw, candidate, size) <= max_width:
            line = candidate
        else:
            if line.strip():
                lines.append(line.rstrip())
            line = tok if tok != " " else ""
    if line.strip():
        lines.append(line.rstrip())
    return lines


def rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def make_card(filename, category, badge_color, title, headline, headline_color,
              bullets, footer_note):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Top color bar
    draw.rectangle([0, 0, W, 12], fill=badge_color)

    # Main card
    margin = 50
    card_box = [margin, 60, W - margin, H - 80]
    rounded_rect(draw, card_box, 24, fill=CARD, outline=BORDER, width=2)

    # Category badge
    bx, by = margin + 40, 100
    badge_text = category
    bw = measure_mixed(draw, badge_text, 26) + 36
    bh = 44
    rounded_rect(draw, [bx, by, bx + bw, by + bh], 22, fill=badge_color)
    draw_mixed(draw, (bx + bw // 2, by + 7), badge_text, 26, "#FFFFFF", anchor="center")

    # Brand top-right
    brand_y = by + 12
    draw_mixed(draw, (W - margin - 40, brand_y), "德國知識小種子", 22, TEXT_LIGHT, anchor="right")

    # Title (large, mixed)
    tx = margin + 40
    ty = by + bh + 30
    title_lines = wrap_mixed(draw, title, 44, W - 2 * margin - 80)
    for ln in title_lines:
        draw_mixed(draw, (tx, ty), ln, 44, TEXT_DARK)
        ty += 56
    ty += 10

    # Divider
    draw.line([(tx, ty), (W - margin - 40, ty)], fill=BORDER, width=2)
    ty += 30

    # Headline (big highlighted number/phrase)
    if headline:
        head_lines = wrap_mixed(draw, headline, 60, W - 2 * margin - 80)
        for ln in head_lines:
            draw_mixed(draw, (tx, ty), ln, 60, headline_color)
            ty += 76
        ty += 18

    # Bullets — each is (dot_color, text)
    for color, text in bullets:
        # Dot
        cx = tx + 12
        cy = ty + 18
        draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=color)
        # Text wrapped
        text_x = tx + 40
        lines = wrap_mixed(draw, text, 28, W - 2 * margin - 80 - 40)
        for i, ln in enumerate(lines):
            draw_mixed(draw, (text_x, ty + i * 38), ln, 28, TEXT_DARK)
        ty += max(38 * len(lines), 38) + 14

    # Footer — two stacked lines so they don't collide
    fy = H - 80 - 80
    draw.line([(margin + 40, fy), (W - margin - 40, fy)], fill=BORDER, width=1)
    # Source note on top line (may be long)
    src_lines = wrap_mixed(draw, footer_note, 19, W - 2 * margin - 80)
    sy = fy + 14
    for ln in src_lines:
        draw_mixed(draw, (margin + 40, sy), ln, 19, TEXT_LIGHT)
        sy += 26
    # Brand date on bottom line
    draw_mixed(draw, (W - margin - 40, fy + 14 + 26 * max(len(src_lines), 1) + 4),
               "Das deutsch Wissen ｜ W21 2026/05/18-22", 19, TEXT_LIGHT, anchor="right")

    path = os.path.join(OUT_DIR, filename)
    img.save(path, "PNG", optimize=True)
    print(f"saved: {path}")
    return path


# --- Card 1: Energy crisis & GDP downgrade ---
make_card(
    filename="W21_圖卡1_伊朗戰爭能源衝擊.png",
    category="經濟 Wirtschaft",
    badge_color=PALETTE["red"],
    title="伊朗戰爭衝擊德國 政府下修 GDP 預測砍半",
    headline="GDP 1.0% → 0.5%",
    headline_color=PALETTE["red"],
    bullets=[
        (PALETTE["red"], "通膨預測上修至 2.7-2.8%，失業率 4 月升至 6.4%（3 月為 6.3%）"),
        (PALETTE["orange"], "復活節高峰：柴油較戰前每公升貴 70 分，E10 貴 41 分"),
        (PALETTE["blue"], "聯盟通過 16 億歐元燃油減稅，柴油與汽油每公升降約 17 分（兩個月）"),
        (PALETTE["purple"], "經濟部長 Reiche (CDU) 與財政部長 Klingbeil (SPD) 為「暴利稅」激烈交鋒"),
    ],
    footer_note="資料：歐盟執委會、ifo、Handelsblatt、ZDF（2026/04-05）",
)

# --- Card 2: Aviation tax cut ---
make_card(
    filename="W21_圖卡2_機票稅調降.png",
    category="政策 Politik",
    badge_color=PALETTE["blue"],
    title="聯邦議院 5/21 通過調降機票稅 7/1 起生效",
    headline="長程 −€11.40 /人",
    headline_color=PALETTE["blue"],
    bullets=[
        (PALETTE["blue"], "短程：€15.53 → €13.03（−€2.50）｜中程：€39.34 → €33.01（−€6.33）"),
        (PALETTE["blue"], "長程：€70.83 → €59.43（−€11.40）— 從德國飛回台灣每張票省約 €11"),
        (PALETTE["green"], "CDU/CSU、SPD、AfD 三黨共同支持，預計減免 3.5 億歐元稅收"),
        (PALETTE["red"], "環團強烈反對：Greenpeace 稱「致命訊號」、BUND 批氣候保護地位低落"),
    ],
    footer_note="資料：t-online、ZDF、Bundestag、Greenpeace、BUND（2026/05/21-22）",
)

# --- Card 3: Blue Card & Bürgergeld changes (foreigners-relevant) ---
make_card(
    filename="W21_圖卡3_藍卡與居留新規.png",
    category="移民 Migration",
    badge_color=PALETTE["teal"],
    title="2026 EU 藍卡門檻調升 Bürgergeld 改名加嚴",
    headline="一般職 €50,700／短缺職 €45,934",
    headline_color=PALETTE["teal"],
    bullets=[
        (PALETTE["teal"], "EU Blue Card 一般職薪資門檻 €48,300 → €50,700（年增 €2,400）"),
        (PALETTE["teal"], "IT/工程/醫療等短缺職：€43,759 → €45,934（年增 €2,175）"),
        (PALETTE["orange"], "Bürgergeld 改名「Neue Grundsicherung」，月領 €563 不變但加強制裁"),
        (PALETTE["purple"], "3 年加速入籍取消，回到 5 年最低；雇主須依 §45c 告知第三國技工權益"),
    ],
    footer_note="資料：BMI、Make it in Germany、The Local、iamexpat（2026 元月起）",
)

print("All cards generated.")
