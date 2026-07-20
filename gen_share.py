# -*- coding: utf-8 -*-
"""
QDII 净值看板 - 微信/社交平台分享预览图 (OG Image)
生成 800x418 PNG，用于 index.html 的 og:image 标签。
微信转发链接时会抓取此图作为卡片封面。
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "share.png")

W, H = 800, 418

# 珊瑚粉配色（和看板 UI 一致）
C_BG_TOP = (255, 158, 133)    # 浅珊瑚
C_BG_BOT = (232, 90, 84)      # 珊瑚红
C_WHITE = (255, 255, 255)
C_INK_DARK = (45, 31, 32)
C_INK_LIGHT = (138, 122, 124)

img = Image.new("RGB", (W, H), C_BG_TOP)
draw = ImageDraw.Draw(img)

# 背景渐变：从上到下珊瑚色渐变
for y in range(H):
    r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * y / H)
    g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * y / H)
    b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * y / H)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# 白色卡片（居中偏下）
card_l, card_t, card_r, card_b = 40, 180, W - 40, H - 35
card_w, card_h = card_r - card_l, card_b - card_t
draw.rounded_rectangle([card_l, card_t, card_r, card_b], radius=18, fill=C_WHITE)

try:
    fnt_title = ImageFont.truetype("msyhbd.ttc", 36)
    fnt_sub = ImageFont.truetype("msyh.ttc", 20)
    fnt_desc = ImageFont.truetype("msyh.ttc", 16)
except:
    fnt_title = ImageFont.load_default()
    fnt_sub = fnt_title
    fnt_desc = fnt_title

# 品牌标题（白色，顶部区域）
title_text = "QDII 全球基金 · 每日净值看板"
tb = draw.textbbox((0, 0), title_text, font=fnt_title)
tw = tb[2] - tb[0]
draw.text(((W - tw) // 2, 55), title_text, fill=C_WHITE, font=fnt_title)

# 副标题（白色半透明感）
sub_text = "覆盖百余只 QDII 基金 · 涨红跌绿一屏掌握"
sb = draw.textbbox((0, 0), sub_text, font=fnt_sub)
sw = sb[2] - sb[0]
draw.text(((W - sw) // 2, 110), sub_text, fill=C_WHITE, font=fnt_sub)

# 卡片内卖点文字
lines = [
    ("覆盖全面", "美股主动基 / 纳斯达克100 / 标普500 / 科技成长"),
    ("每日更新", "自动抓取公开净值数据，每交易日多次刷新"),
    ("走势可查", "点击任意基金查看近30日净值走势图"),
]

y_off = card_t + 22
for label, desc in lines:
    # 标签圆点 + 文字
    draw.ellipse([card_l + 20, y_off + 3, card_l + 32, y_off + 15], fill=(232, 90, 84))
    draw.text((card_l + 42, y_off - 3), label, fill=C_INK_DARK, font=fnt_desc)
    draw.text((card_l + 42 + 72, y_off - 1), desc, fill=C_INK_LIGHT, font=fnt_desc)
    y_off += 38

# 底部引导
guide = "长按识别二维码或点击查看完整看板 →"
gb = draw.textbbox((0, 0), guide, font=fnt_desc)
gw = gb[2] - gb[0]
draw.text((card_l + (card_w - gw) // 2, card_b - 34), guide, fill=C_INK_LIGHT, font=fnt_desc)

img.save(OUT, "PNG", optimize=True)
print(f"OK: {OUT} ({os.path.getsize(OUT)} bytes)")
