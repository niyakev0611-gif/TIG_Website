"""Weekly newsletter cards for 德國知識小種子, W21 (May 18-22, 2026).
Three fresh topics specific to this week (avoiding overlap with W12-W19):
  1) 5/21 Bundestag passes aviation tax cut
  2) 5/19 Merkel receives first European Order of Merit in Strasbourg
  3) Northern Germany ÖPNV strikes + Lufthansa policy push (5/19-21)
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = "/home/user/TIG_Website/sessions/2026-W21/mnt/Claude"

CJK_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
LATIN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG = "#F8F6F2"
CARD = "#FFFFFF"
BORDER = "#E8E4DE"
TEXT_DARK = "#1F2937"
TEXT_GREY = "#6B7280"
TEXT_LIGHT = "#9CA3AF"

PALETTE = {
    "green":  "#2E8B57",
    "red":    "#C0392B",
    "orange": "#D4740E",
    "blue":   "#2563EB",
    "purple": "#7C3AED",
    "teal":   "#0D9488",
}
TINT = {
    "red":    "#FDECEC",
    "orange": "#FDF3E7",
    "blue":   "#E8EFFD",
    "teal":   "#E2F2F0",
    "green":  "#E6F1EB",
    "purple": "#EFE7FD",
    "neutral":"#F1F2F6",
}

W, H = 1080, 1080


def is_cjk(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
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
    return ImageFont.truetype(CJK_FONT, size), ImageFont.truetype(LATIN_FONT, size)


def split_runs(text):
    runs = []
    if not text:
        return runs
    cur = text[0]
    cur_is = is_cjk(cur)
    for ch in text[1:]:
        c = is_cjk(ch)
        if c == cur_is:
            cur += ch
        else:
            runs.append((cur_is, cur))
            cur = ch
            cur_is = c
    runs.append((cur_is, cur))
    return runs


def measure_run(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def measure_mixed(draw, text, size):
    cjk_f, lat_f = load_fonts(size)
    return sum(measure_run(draw, t, cjk_f if c else lat_f) for c, t in split_runs(text))


def draw_mixed(draw, xy, text, size, color, anchor="left"):
    cjk_f, lat_f = load_fonts(size)
    runs = split_runs(text)
    total = sum(measure_run(draw, t, cjk_f if c else lat_f) for c, t in runs)
    x, y = xy
    if anchor == "center":
        x -= total // 2
    elif anchor == "right":
        x -= total
    for c, t in runs:
        f = cjk_f if c else lat_f
        draw.text((x, y), t, font=f, fill=color)
        x += measure_run(draw, t, f)
    return total


def wrap_mixed(draw, text, size, max_w):
    tokens = []
    buf = ""
    for ch in text:
        if is_cjk(ch):
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        else:
            if ch == " " and buf:
                tokens.append(buf)
                tokens.append(" ")
                buf = ""
            else:
                buf += ch
    if buf:
        tokens.append(buf)
    lines, line = [], ""
    for tok in tokens:
        cand = line + tok
        if measure_mixed(draw, cand, size) <= max_w:
            line = cand
        else:
            if line.strip():
                lines.append(line.rstrip())
            line = tok if tok != " " else ""
    if line.strip():
        lines.append(line.rstrip())
    return lines


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def build_card(filename, category_zh, category_de, accent, accent_tint,
               title, subtitle, highlight, stats, footer_date):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Badge & brand
    top_y = 50
    badge_pad_x = 22
    badge_h = 56
    badge_text = f"{category_zh} {category_de}"
    bw = measure_mixed(d, badge_text, 26) + badge_pad_x * 2
    bx = 70
    rounded(d, [bx, top_y, bx + bw, top_y + badge_h], badge_h // 2,
            fill=accent_tint, outline=None)
    draw_mixed(d, (bx + bw // 2, top_y + (badge_h - 32) // 2),
               badge_text, 26, accent, anchor="center")
    draw_mixed(d, (W - 70, top_y + (badge_h - 24) // 2),
               "德國知識小種子", 24, TEXT_GREY, anchor="right")

    # Main card
    card_top = top_y + badge_h + 30
    card_box = [40, card_top, W - 40, H - 60]
    rounded(d, card_box, 28, fill=CARD, outline=BORDER, width=2)

    inner_l = 80
    inner_r = W - 80
    inner_w = inner_r - inner_l
    y = card_top + 56

    # Title
    title_size = 52
    title_lines = wrap_mixed(d, title, title_size, inner_w)
    for ln in title_lines:
        draw_mixed(d, (inner_l, y), ln, title_size, TEXT_DARK)
        y += 68

    # Subtitle
    if subtitle:
        y += 4
        sub_lines = wrap_mixed(d, subtitle, 24, inner_w)
        for ln in sub_lines:
            draw_mixed(d, (inner_l, y), ln, 24, TEXT_GREY)
            y += 34
    y += 28

    # Highlight box
    if highlight:
        box_h = 200
        hl_tint = highlight.get("tint", accent_tint)
        rounded(d, [inner_l, y, inner_r, y + box_h], 18, fill=hl_tint)
        draw_mixed(d, ((inner_l + inner_r) // 2, y + 22),
                   highlight["label_top"], 22, TEXT_GREY, anchor="center")
        if highlight.get("single"):
            # auto-fit value font size so it fits within the box
            avail = inner_r - inner_l - 80
            size = 82
            while size > 32 and measure_mixed(d, highlight["value"], size) > avail:
                size -= 2
            draw_mixed(d, ((inner_l + inner_r) // 2, y + 60 + (82 - size) // 2),
                       highlight["value"], size, accent, anchor="center")
            if highlight.get("sub"):
                draw_mixed(d, ((inner_l + inner_r) // 2, y + 160),
                           highlight["sub"], 22, TEXT_GREY, anchor="center")
        else:
            mid_x = (inner_l + inner_r) // 2
            cl_x = (inner_l + mid_x) // 2
            cr_x = (mid_x + inner_r) // 2
            draw_mixed(d, (cl_x, y + 60), highlight["value_left"], 70,
                       accent, anchor="center")
            draw_mixed(d, (cl_x, y + 150), highlight["label_left"], 22,
                       TEXT_GREY, anchor="center")
            draw_mixed(d, (mid_x, y + 90), highlight.get("middle", "→"),
                       36, TEXT_GREY, anchor="center")
            draw_mixed(d, (cr_x, y + 60), highlight["value_right"], 70,
                       TEXT_DARK, anchor="center")
            draw_mixed(d, (cr_x, y + 150), highlight["label_right"], 22,
                       TEXT_GREY, anchor="center")
        y += box_h + 32

    # Stats rows
    num_col_w = 280
    label_x = inner_l + num_col_w + 30
    row_gap = 16
    for color_key, big, label, desc in stats:
        color = PALETTE[color_key]
        d.ellipse([inner_l - 4, y + 18, inner_l + 10, y + 32], fill=color)
        draw_mixed(d, (inner_l + 22, y), big, 44, color)
        draw_mixed(d, (label_x, y + 4), label, 24, TEXT_DARK)
        desc_lines = wrap_mixed(d, desc, 20, inner_r - label_x)
        ly = y + 36
        for ln in desc_lines:
            draw_mixed(d, (label_x, ly), ln, 20, TEXT_GREY)
            ly += 28
        y += max(60, ly - y) + row_gap

    # Footer
    fy = H - 60 - 46
    left_text = footer_date
    right_text = "德國週報 W21"
    sep = "  |  "
    full_w = measure_mixed(d, left_text + sep + right_text, 22)
    cx = (inner_l + inner_r) // 2
    sx = cx - full_w // 2
    draw_mixed(d, (sx, fy), left_text, 22, TEXT_GREY)
    sx += measure_mixed(d, left_text, 22)
    draw_mixed(d, (sx, fy), sep, 22, TEXT_LIGHT)
    sx += measure_mixed(d, sep, 22)
    draw_mixed(d, (sx, fy), right_text, 22, TEXT_GREY)

    path = os.path.join(OUT_DIR, filename)
    img.save(path, "PNG", optimize=True)
    print(f"saved: {path}")
    return path


# ---------- Card 1: Aviation tax cut (genuinely new this week) ----------
build_card(
    filename="W21_圖卡1_機票稅調降.png",
    category_zh="政策", category_de="Politik",
    accent=PALETTE["blue"], accent_tint=TINT["blue"],
    title="機票稅 7/1 起調降  長程每張省 €11",
    subtitle="聯邦議院 5/21 三黨表決通過｜環團痛批氣候大會期間反向操作",
    highlight={
        "single": True,
        "label_top": "長程航班稅變化（含飛回台灣）",
        "value": "€70.83 → €59.43",
        "sub": "每張票減免 €11.40，2026 年 7 月 1 日起生效",
        "tint": TINT["blue"],
    },
    stats=[
        ("blue",   "−€2.50",  "短程歐洲航線", "€15.53 → €13.03（如柏林飛巴黎）"),
        ("blue",   "−€6.33",  "中程航線",     "€39.34 → €33.01（如歐洲飛中東）"),
        ("green",  "3 黨",    "聯合表決通過", "CDU/CSU + SPD + AfD 一致支持本法案"),
        ("red",    "3.5 億 €", "Greenpeace 痛批「致命訊號」", "BUND：氣候保護地位低落；UBA 反建議加稅"),
    ],
    footer_date="2026.05.18 — 05.22",
)

# ---------- Card 2: Merkel European Order of Merit (5/19) ----------
build_card(
    filename="W21_圖卡2_梅克爾歐洲勳章.png",
    category_zh="文化", category_de="Kultur",
    accent=PALETTE["purple"], accent_tint=TINT["purple"],
    title="梅克爾獲頒首屆歐洲功勳勳章",
    subtitle="5/19 斯特拉斯堡受勳｜與華勒沙、澤倫斯基同列首批得主",
    highlight={
        "single": True,
        "label_top": "Europäischer Verdienstorden｜2026 首屆三位得主",
        "value": "Merkel · Wałęsa · Zelensky",
        "sub": "表彰對歐洲一體化與民主價值的傑出貢獻",
        "tint": TINT["purple"],
    },
    stats=[
        ("purple", "5/19",   "斯特拉斯堡受勳",    "於歐洲議會全會大廳舉行授勳典禮"),
        ("blue",   "16 年",  "前總理任期",       "2005-2021，史上首位東德出身總理"),
        ("teal",   "演講",   "呼籲規範社群媒體", "強調對和平、繁榮、民主的承諾"),
        ("orange", "三人",   "獲獎者背景多元",   "前總理／團結工聯領袖／戰時烏克蘭總統"),
    ],
    footer_date="2026.05.18 — 05.22",
)

# ---------- Card 3: Strike wave & Lufthansa policy push (life reminder) ----------
build_card(
    filename="W21_圖卡3_本週交通提醒.png",
    category_zh="生活", category_de="Leben",
    accent=PALETTE["orange"], accent_tint=TINT["orange"],
    title="本週德國交通三件大事  在德生活提醒",
    subtitle="北德 ÖPNV 罷工持續｜Lufthansa 政策呼籲限制罷工權",
    highlight={
        "label_top": "ver.di 北德公共運輸罷工｜5/19-21",
        "value_left": "Göttingen",
        "label_left": "5/19-20 公車電車停擺",
        "value_right": "Hannover",
        "label_right": "5/20-21 ÜSTRA + Regiobus",
        "middle": "＋",
        "tint": TINT["orange"],
    },
    stats=[
        ("orange", "下薩克森", "ÖPNV 罷工最後堡壘", "全國多數已達協議，僅 Niedersachsen 仍在抗爭"),
        ("blue",   "5/20",   "Lufthansa 政策呼籲", "要求政府立法限制「關鍵基礎建設」罷工權"),
        ("red",    "2 萬班", "CityLine 關閉影響",  "4 月關閉的支線子公司，10 月前短程航班持續取消"),
        ("teal",   "5/21",   "EU 春季預測加重",   "布魯塞爾將德 GDP 從 1.2% 砍至 0.6%（背景參考）"),
    ],
    footer_date="2026.05.18 — 05.22",
)

print("All cards generated.")
