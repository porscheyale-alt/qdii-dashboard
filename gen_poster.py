# -*- coding: utf-8 -*-
"""生成对客海报：竖版，珊瑚粉金融风（与看板UI一致），中部二维码卡片直达看板。"""
import os
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image, ImageDraw, ImageFont

SITE_URL = "https://porscheyale-alt.github.io/qdii-dashboard/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "poster.png")

W, H = 1080, 1920

# 珊瑚粉配色（与看板 UI 一致）
C_BG_TOP = (255, 246, 246)    # 极浅粉底
C_BG_BOT = (255, 230, 228)    # 浅暖粉
C_ACCENT = (232, 90, 84)      # 珊瑚红（主色）
C_ACCENT_LIGHT = (255, 158, 133)  # 浅珊瑚
C_DARK = (45, 31, 32)         # 深墨字
C_SUB = (138, 122, 124)       # 次要文字
C_WHITE = (255, 255, 255)
C_CARD_BG = (255, 255, 255)

FDIR = r"C:\Windows\Fonts"
def font(name, size):
    return ImageFont.truetype(os.path.join(FDIR, name), size)

f_brand = font("msyhbd.ttc", 30)
f_h1    = font("msyhbd.ttc", 72)
f_h2    = font("msyhbd.ttc", 52)
f_sub   = font("msyh.ttc", 30)
f_tip   = font("msyhbd.ttc", 38)
f_pts   = font("msyh.ttc", 26)
f_small = font("msyh.ttc", 22)
f_tag   = font("msyhbd.ttc", 26)

# --- 渐变背景 ---
img = Image.new("RGB", (W, H), C_BG_TOP)
d = ImageDraw.Draw(img)
for y in range(H):
    t = y / H
    r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * t)
    g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * t)
    b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

def ctext(y, text, fnt, fill, cx=W//2):
    bbox = d.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    d.text((cx - w/2, y), text, font=fnt, fill=fill)
    return bbox[3] - bbox[1]

# --- 顶部品牌标签（珊瑚红胶囊）---
brand_text = "QDII 全球基金"
bb = d.textbbox((0, 0), brand_text, font=f_brand)
bw = bb[2] - bb[0] + 48
bh = bb[3] - bb[1] + 20
bx0 = (W - bw) // 2
by0 = 100
d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=bh//2, fill=C_ACCENT)
ctext(by0 + 10, brand_text, f_brand, C_WHITE)

# --- 主标题区 ---
ctext(210, "每日净值看板", f_h1, C_DARK)
ctext(310, "全球资产 · 一屏掌握", f_h2, C_ACCENT)

# --- 装饰分隔线 ---
lw = 120
d.rounded_rectangle([W//2 - lw, 410, W//2 + lw, 416], radius=3, fill=C_ACCENT_LIGHT)

# --- 卖点副说明 ---
ctext(450, "覆盖美股主动基 · 纳斯达克 · 标普 500 · 科技成长", f_sub, C_SUB)
ctext(500, "每个交易日多次更新，净值随行就市", f_sub, C_SUB)

# --- 中部白色圆角卡片（二维码）---
card_w, card_h = 760, 800
cx0 = (W - card_w) // 2
cy0 = 600
d.rounded_rectangle([cx0, cy0, cx0 + card_w, cy0 + card_h], radius=36, fill=C_CARD_BG)

# 卡片内标题
ctext(cy0 + 56, "扫码查看完整看板", f_tip, C_DARK)

# 二维码
qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=12, border=1)
qr.add_data(SITE_URL)
qr.make(fit=True)
qr_img = qr.make_image(fill_color=C_DARK, back_color="white").convert("RGB")
QR = 480
qr_img = qr_img.resize((QR, QR), Image.NEAREST)
qx = (W - QR) // 2
qy = cy0 + 140
img.paste(qr_img, (qx, qy))

# 二维码下引导文字
ctext(qy + QR + 44, "微信长按识别 · 或用相机扫码", f_pts, C_SUB)

# 卡片内装饰线
cw2 = 80
d.rounded_rectangle([cx0 + card_w//2 - cw2, cy0 + card_h - 70, cx0 + card_w//2 + cw2, cy0 + card_h - 64], radius=3, fill=C_ACCENT_LIGHT)

# --- 底部三个卖点标签（胶囊样式）---
py = cy0 + card_h + 64
tags = ["净值每日多次刷新", "涨跌一目了然", "覆盖百余只 QDII"]
tag_gap = W // 3
for i, txt in enumerate(tags):
    tcx = tag_gap * i + tag_gap // 2
    tb = d.textbbox((0, 0), txt, font=f_tag)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    padx, pady = 28, 14
    tx0 = tcx - tw // 2 - padx
    ty0 = py - pady
    d.rounded_rectangle([tx0, ty0, tx0 + tw + padx*2, ty0 + th + pady*2], radius=(th + pady*2)//2, fill=C_WHITE)
    # 轻描边
    d.rounded_rectangle([tx0, ty0, tx0 + tw + padx*2, ty0 + th + pady*2], radius=(th + pady*2)//2, outline=C_ACCENT_LIGHT, width=1)
    ctext(ty0 + pady, txt, f_tag, C_DARK, cx=tcx)

# --- 底部合规声明 ---
disc_y = H - 140
dw = W - 160
d.rounded_rectangle([80, disc_y - 20, W - 80, disc_y - 14], radius=2, fill=C_ACCENT_LIGHT)
ctext(disc_y, "市场有风险，投资需谨慎。过往业绩不预示未来表现。", f_small, C_SUB)
ctext(disc_y + 30, "本内容仅供参考，不构成任何投资建议。完整风险揭示以看板页面为准。", f_small, C_SUB)

img.save(OUT, "PNG")
print("已生成海报 ->", OUT)
