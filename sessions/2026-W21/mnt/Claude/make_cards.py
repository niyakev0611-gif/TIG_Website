"""Weekly newsletter cards for 德國知識小種子, W21 (May 18-22, 2026).
Three fresh topics specific to this week (avoiding overlap with W12-W19):
  1) 5/21 Bundestag passes aviation tax cut
  2) 5/20 SC Freiburg loses 0-3 to Aston Villa in Europa League final
  3) 5/19 E-Auto purchase subsidy opens for online application at BAFA
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


# ---------- Card 1: Aviation tax cut (5/21 Bundestag) ----------
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

# ---------- Card 2: SC Freiburg Europa League final loss (5/20) ----------
build_card(
    filename="W21_圖卡2_Freiburg歐霸盃決賽.png",
    category_zh="體育", category_de="Sport",
    accent=PALETTE["red"], accent_tint=TINT["red"],
    title="Freiburg 寫歷史卻惜敗  歐霸盃決賽 0:3 不敵 Aston Villa",
    subtitle="5/20 伊斯坦堡｜德甲球隊生涯首次踢進歐洲決賽",
    highlight={
        "single": True,
        "label_top": "UEFA Europa League Final｜Beşiktaş Park",
        "value": "0 : 3",
        "sub": "2026/05/20 21:00 CET｜伊斯坦堡 · 雙方首次歐霸盃決賽",
        "tint": TINT["red"],
    },
    stats=[
        ("red",    "41′",    "Tielemans 開局轉折",  "短角球配合 Rogers 後禁區內凌空抽射破門"),
        ("red",    "45+3′",  "Buendía 半場前致命",  "禁區邊緣弧線球，打進左上死角擴大領先"),
        ("red",    "58′",    "Rogers 鎖定勝局",     "第三球終結懸念，引爆 Villa 球迷狂歡"),
        ("orange", "44 年",  "Aston Villa 終於登頂", "自 1982 歐冠以來首座歐洲獎盃，首奪歐霸盃"),
    ],
    footer_date="2026.05.18 — 05.22",
)

# ---------- Card 3: E-Auto purchase subsidy opens (5/19 BAFA) ----------
build_card(
    filename="W21_圖卡3_電動車補助開放.png",
    category_zh="補助", category_de="Förderung",
    accent=PALETTE["green"], accent_tint=TINT["green"],
    title="E-Auto 購車補助 5/19 起開放申請",
    subtitle="BAFA 線上受理｜最高 €6,000，家庭年所得 €80,000 以下可申請",
    highlight={
        "label_top": "Elektroauto-Kaufprämie 2026｜BAFA 補助方案",
        "value_left": "€6,000",
        "label_left": "依收入最高補助",
        "value_right": "30 億 €",
        "label_right": "總預算 ≈ 80 萬輛車",
        "middle": "／",
        "tint": TINT["green"],
    },
    stats=[
        ("green",  "€80,000",  "家庭年所得上限",   "每多 1 個孩子寬限 +€5,000，最高 €90,000"),
        ("teal",   "2026/1/1", "回溯適用",         "今年初首次在德國登記的純電車皆可申請"),
        ("orange", "36 個月",  "強制持有期",       "申請後須持有滿 3 年，違者須返還補助"),
        ("purple", "線上申請", "foerderzentrale.gov.de", "申請流程全數位化；僅私人 PKW 適用，二手車不支援"),
    ],
    footer_date="2026.05.18 — 05.22",
)

print("All cards generated.")
