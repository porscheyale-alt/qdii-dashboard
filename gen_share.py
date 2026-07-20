# -*- coding: utf-8 -*-
"""
QDII 净值看板 - 微信/社交平台分享预览图 (OG Image)
生成 500x500 PNG，用于 index.html 的 og:image 标签。
简洁风格：仅标题「QDII信息看板」+ 珊瑚粉渐变背景。
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "share.png")

W, H = 500, 500

# 珊瑚粉配色（和看板 UI 一致）
C_BG_TOP = (255, 158, 133)
C_BG_BOT = (232, 90, 84)
C_WHITE = (255, 255, 255)

img = Image.new("RGB", (W, H), C_BG_TOP)
draw = ImageDraw.Draw(img)

# 背景渐变：从上到下珊瑚色渐变
for y in range(H):
    r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * y / H)
    g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * y / H)
    b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * y / H)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

try:
    fnt_title = ImageFont.truetype("msyhbd.ttc", 48)
except:
    fnt_title = ImageFont.load_default()

# 居中显示「QDII信息看板」
title_text = "QDII信息看板"
tb = draw.textbbox((0, 0), title_text, font=fnt_title)
tw = tb[2] - tb[0]
th = tb[3] - tb[1]
draw.text(((W - tw) // 2, (H - th) // 2), title_text, fill=C_WHITE, font=fnt_title)

img.save(OUT, "PNG", optimize=True)
print(f"OK: {OUT} ({os.path.getsize(OUT)} bytes)")
