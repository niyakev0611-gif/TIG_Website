"""
德國週報 W22 (2026-05-25 ~ 2026-05-31) 圖卡產生器
1080x1080 PNG, 雙字體系統, 柔和淺色風格
"""
from PIL import Image, ImageDraw, ImageFont
import os, unicodedata

# 字體路徑（容器內可用字體）
CJK_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"  # 中文 fallback
LATIN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # 英數符號

# 顏色 (柔和淺色風格)
BG = (248, 246, 242)        # #F8F6F2 暖奶油色背景
CARD_BG = (255, 255, 255)   # 白色卡片
BORDER = (232, 228, 222)    # #E8E4DE 邊框
TEXT_DARK = (40, 40, 50)
TEXT_GRAY = (110, 110, 120)
TEXT_LIGHT = (160, 160, 170)

# 主題顏色
GREEN = (46, 139, 87)       # #2E8B57
RED = (192, 57, 43)         # #C0392B
ORANGE = (212, 116, 14)     # #D4740E
BLUE = (37, 99, 235)        # #2563EB
PURPLE = (124, 58, 237)     # #7C3AED
TEAL = (13, 148, 136)       # #0D9488


def is_cjk(ch):
    """判斷字元是否為 CJK"""
    if not ch:
        return False
    cp = ord(ch)
    # CJK Unified Ideographs / Compatibility / Extension A
    if 0x4E00 <= cp <= 0x9FFF: return True
    if 0x3400 <= cp <= 0x4DBF: return True
    if 0xF900 <= cp <= 0xFAFF: return True
    # 全形標點
    if 0x3000 <= cp <= 0x303F: return True
    if 0xFF00 <= cp <= 0xFFEF: return True
    # 注音、平假名、片假名
    if 0x3040 <= cp <= 0x31FF: return True
    return False


def get_font(cjk, size):
    if cjk:
        return ImageFont.truetype(CJK_FONT, size)
    return ImageFont.truetype(LATIN_FONT, size)


def measure(text, size):
    """量測混排寬度"""
    w = 0
    h = 0
    for ch in text:
        f = get_font(is_cjk(ch), size)
        bbox = f.getbbox(ch)
        w += bbox[2] - bbox[0]
        h = max(h, bbox[3] - bbox[1])
    return w, h


def draw_mixed(draw, xy, text, size, fill, anchor='lt'):
    """逐字判斷 CJK 切換字體，支援 anchor='center'/'right'/'lt'"""
    x, y = xy
    total_w, total_h = measure(text, size)
    if anchor in ('center', 'mm', 'mt', 'mb'):
        x = x - total_w // 2
    elif anchor in ('right', 'rt', 'rm', 'rb'):
        x = x - total_w
    cur_x = x
    for ch in text:
        f = get_font(is_cjk(ch), size)
        bbox = f.getbbox(ch)
        draw.text((cur_x, y), ch, font=f, fill=fill)
        cur_x += bbox[2] - bbox[0]
    return total_w


def rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def make_base(title_cn, title_en, badge_text, accent):
    """產生底圖：背景、頂部色條、品牌、badge、footer"""
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # 頂部色條
    draw.rectangle([0, 0, W, 14], fill=accent)

    # 品牌名 (右上)
    draw_mixed(draw, (W - 48, 48), "德國知識小種子", 26, TEXT_GRAY, anchor='right')
    draw_mixed(draw, (W - 48, 82), "Das deutsche Wissen", 18, TEXT_LIGHT, anchor='right')

    # 分類 badge (左上)
    badge_w = measure(badge_text, 22)[0] + 36
    rounded_rect(draw, [48, 48, 48 + badge_w, 88], radius=20, fill=accent)
    draw_mixed(draw, (48 + 18, 56), badge_text, 22, (255, 255, 255))

    # 主標題
    draw_mixed(draw, (W // 2, 130), title_cn, 56, TEXT_DARK, anchor='center')
    draw_mixed(draw, (W // 2, 205), title_en, 24, TEXT_GRAY, anchor='center')

    # 分隔線
    draw.line([(120, 248), (W - 120, 248)], fill=BORDER, width=2)

    # Footer
    draw.line([(48, H - 80), (W - 48, H - 80)], fill=BORDER, width=1)
    draw_mixed(draw, (48, H - 60), "2026/5/25 – 5/31  W22", 20, TEXT_GRAY)
    draw_mixed(draw, (W - 48, H - 60), "德國知識小種子｜Weekly", 20, TEXT_GRAY, anchor='right')

    return img, draw


def data_card(draw, xy, w, h, dot_color, label, value, value_color=None, unit=""):
    """卡片：圓點 + label + 大數據"""
    x, y = xy
    rounded_rect(draw, [x, y, x + w, y + h], radius=20,
                 fill=CARD_BG, outline=BORDER, width=2)
    # 左上圓點
    draw.ellipse([x + 24, y + 28, x + 44, y + 48], fill=dot_color)
    # label
    draw_mixed(draw, (x + 60, y + 26), label, 22, TEXT_GRAY)
    # value
    vc = value_color if value_color else TEXT_DARK
    draw_mixed(draw, (x + 24, y + 68), value, 56, vc)
    # unit
    if unit:
        vw = measure(value, 56)[0]
        draw_mixed(draw, (x + 24 + vw + 12, y + 100), unit, 22, TEXT_GRAY)


# ========== 圖卡 1：能源衝擊與通膨 ==========
def card1():
    img, draw = make_base(
        "能源衝擊持續延燒",
        "Iran War Pushes Energy & Inflation Higher",
        "經濟 Wirtschaft",
        ORANGE,
    )
    W = 1080
    # 副標
    draw_mixed(draw, (W // 2, 275),
               "伊朗戰爭推升油氣價格  4月通膨創2年新高",
               26, TEXT_DARK, anchor='center')

    # 2x2 數據卡
    cw, ch = 470, 180
    gap = 30
    sx = (W - cw * 2 - gap) // 2
    sy = 340

    data_card(draw, (sx, sy), cw, ch, ORANGE,
              "4月通膨率 (CPI)", "2.9", value_color=RED, unit="%")
    data_card(draw, (sx + cw + gap, sy), cw, ch, RED,
              "能源價格年增", "+10.1", value_color=RED, unit="%")
    data_card(draw, (sx, sy + ch + gap), cw, ch, BLUE,
              "油價／柴油上看", "2.07", value_color=ORANGE, unit="€/L")
    data_card(draw, (sx + cw + gap, sy + ch + gap), cw, ch, GREEN,
              "政府油稅減免", "16", value_color=GREEN, unit="億歐元")

    # 重點說明卡
    by = sy + (ch + gap) * 2
    rounded_rect(draw, [sx, by, sx + cw * 2 + gap, by + 170],
                 radius=20, fill=CARD_BG, outline=BORDER, width=2)
    draw_mixed(draw, (sx + 30, by + 24), "重點觀察", 22, ORANGE)
    draw_mixed(draw, (sx + 30, by + 60),
               "● 4月通膨2.9%為2024年1月以來最高", 22, TEXT_DARK)
    draw_mixed(draw, (sx + 30, by + 95),
               "● 經濟部下修2026 GDP預測至0.5%", 22, TEXT_DARK)
    draw_mixed(draw, (sx + 30, by + 130),
               "● 油稅減免7/1上路 為期兩個月", 22, TEXT_DARK)

    img.save("/home/user/TIG_Website/output_cards/W22_圖卡1_能源衝擊.png", "PNG")
    print("Saved card 1")


# ========== 圖卡 2：AfD 民調反超 CDU ==========
def card2():
    img, draw = make_base(
        "AfD 民調首度反超 CDU",
        "AfD Overtakes CDU in May Polls",
        "政治 Politik",
        RED,
    )
    W = 1080
    draw_mixed(draw, (W // 2, 275),
               "Merz 支持率持續下滑  黨內換相聲浪浮現",
               26, TEXT_DARK, anchor='center')

    # 民調長條圖區
    cx = 120
    cy = 340
    cw = W - 240
    ch = 280
    rounded_rect(draw, [cx, cy, cx + cw, cy + ch], radius=20,
                 fill=CARD_BG, outline=BORDER, width=2)
    draw_mixed(draw, (cx + 30, cy + 24), "2026年5月聯邦民調", 22, TEXT_GRAY)

    # 長條
    parties = [
        ("AfD", 27, RED),
        ("CDU/CSU", 25, BLUE),
        ("SPD", 14, (220, 100, 30)),
        ("Grüne", 11, GREEN),
        ("Linke", 9, PURPLE),
    ]
    bar_x = cx + 200
    bar_y0 = cy + 75
    max_w = cw - 280
    for i, (name, pct, col) in enumerate(parties):
        y = bar_y0 + i * 38
        # 黨名
        draw_mixed(draw, (cx + 30, y + 2), name, 22, TEXT_DARK)
        # bar
        bw = int(max_w * pct / 35)
        rounded_rect(draw, [bar_x, y, bar_x + bw, y + 26], radius=8, fill=col)
        # 數字
        draw_mixed(draw, (bar_x + bw + 12, y), f"{pct}%", 22, TEXT_DARK)

    # Merz 卡
    sx = 120
    sy = cy + ch + 30
    cw2 = (W - 240 - 30) // 2
    rounded_rect(draw, [sx, sy, sx + cw2, sy + 150], radius=20,
                 fill=CARD_BG, outline=BORDER, width=2)
    draw.ellipse([sx + 24, sy + 28, sx + 44, sy + 48], fill=BLUE)
    draw_mixed(draw, (sx + 60, sy + 26), "Merz 總理支持率", 22, TEXT_GRAY)
    draw_mixed(draw, (sx + 24, sy + 60), "45", 56, BLUE)
    vw = measure("45", 56)[0]
    draw_mixed(draw, (sx + 24 + vw + 12, sy + 92), "%", 22, TEXT_GRAY)
    draw_mixed(draw, (sx + 24, sy + 118), "黨內換相討論升溫", 20, TEXT_GRAY)

    # Sachsen-Anhalt 卡
    sx2 = sx + cw2 + 30
    rounded_rect(draw, [sx2, sy, sx2 + cw2, sy + 150], radius=20,
                 fill=CARD_BG, outline=BORDER, width=2)
    draw.ellipse([sx2 + 24, sy + 28, sx2 + 44, sy + 48], fill=RED)
    draw_mixed(draw, (sx2 + 60, sy + 26), "薩克森-安哈爾特 AfD", 22, TEXT_GRAY)
    draw_mixed(draw, (sx2 + 24, sy + 60), "39-40", 56, RED)
    vw = measure("39-40", 56)[0]
    draw_mixed(draw, (sx2 + 24 + vw + 12, sy + 92), "%", 22, TEXT_GRAY)
    draw_mixed(draw, (sx2 + 24, sy + 118), "州選將至 領先 CDU 12%", 20, TEXT_GRAY)

    img.save("/home/user/TIG_Website/output_cards/W22_圖卡2_AfD民調.png", "PNG")
    print("Saved card 2")


# ========== 圖卡 3：經濟回穩與藍卡新門檻 ==========
def card3():
    img, draw = make_base(
        "經濟微露曙光 藍卡門檻調漲",
        "ifo Up, Q1 GDP +0.3%  Blue Card Threshold Raised",
        "經濟＋移民",
        TEAL,
    )
    W = 1080
    draw_mixed(draw, (W // 2, 275),
               "商業景氣指數連2月回升  藍卡薪資門檻 +5%",
               26, TEXT_DARK, anchor='center')

    cw, ch = 470, 180
    gap = 30
    sx = (W - cw * 2 - gap) // 2
    sy = 340

    data_card(draw, (sx, sy), cw, ch, GREEN,
              "ifo 商業景氣 5月", "84.9", value_color=GREEN, unit="點")
    data_card(draw, (sx + cw + gap, sy), cw, ch, BLUE,
              "Q1 GDP 季增", "+0.3", value_color=GREEN, unit="%")
    data_card(draw, (sx, sy + ch + gap), cw, ch, TEAL,
              "藍卡標準薪資門檻", "50,700", value_color=TEAL, unit="€/年")
    data_card(draw, (sx + cw + gap, sy + ch + gap), cw, ch, PURPLE,
              "緊缺職業門檻", "45,934", value_color=PURPLE, unit="€/年")

    # 對在德外國人提醒
    by = sy + (ch + gap) * 2
    rounded_rect(draw, [sx, by, sx + cw * 2 + gap, by + 170],
                 radius=20, fill=CARD_BG, outline=BORDER, width=2)
    draw_mixed(draw, (sx + 30, by + 24), "對在德外國人的影響", 22, TEAL)
    draw_mixed(draw, (sx + 30, by + 60),
               "● Blue Card 薪資門檻較2025上調約5%", 22, TEXT_DARK)
    draw_mixed(draw, (sx + 30, by + 95),
               "● 機會卡(Chancenkarte)存款門檻 13,092€/年", 22, TEXT_DARK)
    draw_mixed(draw, (sx + 30, by + 130),
               "● 入籍年限恢復8年 (黑紅政府取消5年新制)", 22, TEXT_DARK)

    img.save("/home/user/TIG_Website/output_cards/W22_圖卡3_經濟移民.png", "PNG")
    print("Saved card 3")


if __name__ == "__main__":
    card1()
    card2()
    card3()
    print("All cards generated.")
