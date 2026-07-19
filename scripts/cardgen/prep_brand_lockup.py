# -*- coding: utf-8 -*-
"""品牌 lockup 去背轉檔：Claude Design 原稿 → 圖卡用透明 PNG
================================================================
來源（勿改動）：assets/images/Social Media/brand_手寫風.png
　　（用戶 2026/07 以 Claude Design 定稿：手寫字＋小6圈底線＋🌱）
輸出：scripts/cardgen/brand_lockup.png（去背＋裁邊，paste_wordmark 讀這個）

去背用「與背景色的最大通道距離」當 alpha——灰階法會毀掉彩色的 🌱。
原稿更新後重跑本腳本＋重產圖卡即可。
"""
import os
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'assets', 'images', 'Social Media', 'brand_手寫風.png')
OUT = os.path.join(HERE, 'brand_lockup.png')

img = Image.open(SRC).convert('RGB')
bg = img.getpixel((0, 0))
diff = ImageChops.difference(img, Image.new('RGB', img.size, bg))
r, g, b = diff.split()
dist = ImageChops.lighter(ImageChops.lighter(r, g), b)
# 距離 <8 視為背景、>110 視為全不透明，中間線性（保留反鋸齒邊緣）
alpha = dist.point(lambda v: 0 if v < 8 else min(255, round((v - 8) * 255 / 102)))

bbox = alpha.point(lambda v: 255 if v > 12 else 0).getbbox()
pad = 8
x0 = max(0, bbox[0]-pad); y0 = max(0, bbox[1]-pad)
x1 = min(img.width, bbox[2]+pad); y1 = min(img.height, bbox[3]+pad)

out = img.convert('RGBA')
out.putalpha(alpha)
out = out.crop((x0, y0, x1, y1))
out.save(OUT)
print('✅', OUT, out.size, f'(ink bbox {bbox})')
