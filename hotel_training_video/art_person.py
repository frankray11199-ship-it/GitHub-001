# -*- coding: utf-8 -*-
"""程序化绘制前台接待员角色（亚洲女性 · 职业装 · 半身）。

render_person(mouth, eye) 返回 RGBA 半身像，可叠加到大堂背景上。
mouth: 0 闭口微笑 / 1 微张 / 2 半开 / 3 张开   —— 口型动画
eye:   0 睁眼 / 1 半闭 / 2 闭眼               —— 眨眼
"""

from PIL import Image, ImageDraw, ImageFilter

# ----------------------------------------------------------------- 调色板
SKIN = (240, 208, 184)
SKIN_SH = (219, 182, 158)
SKIN_HI = (249, 228, 210)
HAIR = (43, 33, 34)
HAIR_HI = (78, 61, 60)
BLAZER = (41, 54, 79)
BLAZER_D = (29, 39, 58)
BLAZER_L = (56, 72, 102)
BLOUSE = (247, 246, 242)
BLOUSE_SH = (223, 221, 215)
SCARF = (172, 62, 64)
SCARF_D = (136, 46, 48)
GOLD = (206, 166, 86)
LIP = (198, 108, 110)
LIP_D = (162, 76, 80)
MOUTH_IN = (122, 56, 58)
BROW = (58, 44, 45)
EYE_W = (253, 251, 249)
IRIS = (72, 48, 40)
PUPIL = (26, 18, 16)
BLUSH = (238, 172, 160)

CANVAS = (960, 1280)
SS = 3

# 关键骨架参数
CX = 480
HEAD_CY = 320
HEAD_RX = 122
HEAD_RY = 142
SH_Y = 574                 # 肩线


def render_person(mouth=0, eye=0, scale=SS):
    S = scale
    W, H = CANVAS[0] * S, CANVAS[1] * S
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(x, y):
        return (int(x * S), int(y * S))

    def R(v):
        return int(v * S)

    def ell(dr, cx, cy, rx, ry, **kw):
        dr.ellipse([R(cx - rx), R(cy - ry), R(cx + rx), R(cy + ry)], **kw)

    cx, hcy = CX, HEAD_CY
    hrx, hry = HEAD_RX, HEAD_RY

    # ============================================================ 后层头发
    ell(d, cx, hcy - 6, hrx + 22, hry + 18, fill=HAIR)
    # 盘发（后脑发髻）
    ell(d, cx + 112, hcy - 88, 60, 56, fill=HAIR)
    ell(d, cx + 112, hcy - 88, 42, 39, fill=HAIR_HI)
    ell(d, cx + 112, hcy - 88, 27, 25, fill=HAIR)

    # ============================================================ 颈部
    # 颈部一直画到衣领之下，避免下巴与领口之间露出空隙
    d.polygon([P(cx - 44, hcy + 80), P(cx + 44, hcy + 80),
               P(cx + 56, SH_Y - 26), P(cx - 56, SH_Y - 26)], fill=SKIN_SH)
    d.polygon([P(cx - 38, hcy + 80), P(cx + 28, hcy + 80),
               P(cx + 38, SH_Y - 26), P(cx - 48, SH_Y - 26)], fill=SKIN)
    # 下颌投在颈部的阴影
    nsh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    nd2 = ImageDraw.Draw(nsh)
    ell(nd2, cx, hcy + 128, 60, 30, fill=(178, 140, 118, 165))
    nsh = nsh.filter(ImageFilter.GaussianBlur(R(13)))
    img = Image.alpha_composite(img, nsh)
    d = ImageDraw.Draw(img)

    # ============================================================ 西装外套
    # 由颈根斜出肩峰，再近乎垂直落下，形成真实的肩线而非斗篷
    body = [
        P(cx - 48, SH_Y - 58), P(cx + 48, SH_Y - 58),
        P(cx + 196, SH_Y + 8), P(cx + 228, CANVAS[1]),
        P(cx - 228, CANVAS[1]), P(cx - 196, SH_Y + 8),
    ]
    d.polygon(body, fill=BLAZER)
    # 左肩受光
    d.polygon([P(cx - 48, SH_Y - 56), P(cx - 6, SH_Y - 58),
               P(cx - 132, SH_Y + 46), P(cx - 196, SH_Y + 14)], fill=BLAZER_L)
    # 右侧背光
    d.polygon([P(cx + 150, SH_Y + 40), P(cx + 196, SH_Y + 10),
               P(cx + 228, CANVAS[1]), P(cx + 168, CANVAS[1])], fill=BLAZER_D)

    # 衬衫 V 领
    d.polygon([P(cx - 72, SH_Y - 52), P(cx + 72, SH_Y - 52),
               P(cx + 54, SH_Y + 96), P(cx, SH_Y + 172), P(cx - 54, SH_Y + 96)],
              fill=BLOUSE)
    d.polygon([P(cx + 14, SH_Y - 52), P(cx + 72, SH_Y - 52),
               P(cx + 54, SH_Y + 96), P(cx + 10, SH_Y + 142)], fill=BLOUSE_SH)

    # 丝巾
    d.polygon([P(cx - 66, SH_Y - 56), P(cx + 66, SH_Y - 56),
               P(cx + 48, SH_Y - 4), P(cx, SH_Y + 26), P(cx - 48, SH_Y - 4)],
              fill=SCARF)
    d.polygon([P(cx + 6, SH_Y - 56), P(cx + 66, SH_Y - 56),
               P(cx + 48, SH_Y - 4), P(cx + 8, SH_Y + 18)], fill=SCARF_D)
    ell(d, cx, SH_Y + 8, 20, 16, fill=SCARF_D)
    ell(d, cx, SH_Y + 5, 13, 10, fill=GOLD)

    # 翻领
    d.polygon([P(cx - 80, SH_Y - 54), P(cx - 62, SH_Y + 82),
               P(cx - 6, SH_Y + 186), P(cx - 142, SH_Y + 96)], fill=BLAZER_D)
    d.polygon([P(cx + 80, SH_Y - 54), P(cx + 62, SH_Y + 82),
               P(cx + 6, SH_Y + 186), P(cx + 142, SH_Y + 96)], fill=BLAZER_D)

    # 工牌
    bx, by = cx + 142, SH_Y + 170
    d.rounded_rectangle([R(bx - 56), R(by - 23), R(bx + 56), R(by + 23)],
                        radius=R(6), fill=(246, 244, 238), outline=GOLD, width=R(3))
    d.rectangle([R(bx - 42), R(by - 11), R(bx + 16), R(by - 4)], fill=(120, 128, 144))
    d.rectangle([R(bx - 42), R(by + 3), R(bx + 34), R(by + 9)], fill=(166, 172, 184))

    # ============================================================ 头部
    ell(d, cx, hcy, hrx, hry, fill=SKIN)
    # 下颌（收窄的圆润下巴）
    d.polygon([P(cx - hrx + 4, hcy + 30), P(cx + hrx - 4, hcy + 30),
               P(cx + 52, hcy + hry - 2), P(cx - 52, hcy + hry - 2)], fill=SKIN)
    ell(d, cx, hcy + 92, 68, 58, fill=SKIN)
    # 面部受光
    ell(d, cx - 30, hcy - 20, 56, 70, fill=SKIN_HI)

    # 耳朵 + 耳钉
    for sx in (-1, 1):
        ell(d, cx + sx * (hrx - 2), hcy + 22, 18, 27, fill=SKIN_SH)
        ell(d, cx + sx * (hrx - 4), hcy + 22, 10, 16, fill=SKIN)
        ell(d, cx + sx * (hrx - 4), hcy + 46, 6, 6, fill=GOLD)

    # ============================================================ 前层头发（侧分刘海）
    # 先铺满头顶，再用一个偏右下的椭圆“挖”出额头与整张脸，
    # 剩下的部分自然形成左厚右薄的侧分刘海（不会压到面部）
    hair = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hair)
    hd.ellipse([R(cx - hrx - 13), R(hcy - hry - 15),
                R(cx + hrx + 13), R(hcy + hry * 0.55)], fill=HAIR)
    # 挖脸：椭圆略小于面部轮廓并向右下偏移
    hd.ellipse([R(cx - hrx + 18), R(hcy - hry + 50),
                R(cx + hrx + 24), R(hcy + hry * 1.10)], fill=(0, 0, 0, 0))
    # 刘海边缘的柔和高光（沿发际走向，不做成方块）
    hd.line([P(cx - 104, hcy - 78), P(cx - 78, hcy - 116),
             P(cx - 22, hcy - 134)], fill=HAIR_HI, width=R(15), joint="curve")
    img = Image.alpha_composite(img, hair)

    # 耳侧垂下的发丝：画在面部轮廓之外，避免出现横穿脸颊的黑纹
    d = ImageDraw.Draw(img)
    for sx in (-1, 1):
        d.polygon([P(cx + sx * (hrx + 13), hcy - 60), P(cx + sx * (hrx - 10), hcy - 64),
                   P(cx + sx * (hrx - 6), hcy + 6), P(cx + sx * (hrx + 15), hcy - 4)],
                  fill=HAIR)

    # ============================================================ 五官
    eye_y = hcy + 20
    eye_dx = 50
    ew = 32
    eh = 16

    for sx in (-1, 1):
        ex = cx + sx * eye_dx
        # 眉毛（细而带弧度）
        d.line([P(ex - sx * 30, eye_y - 52), P(ex - sx * 4, eye_y - 62),
                P(ex + sx * 27, eye_y - 54)], fill=BROW, width=R(6), joint="curve")

        if eye == 2:
            d.arc([R(ex - ew), R(eye_y - eh + 2), R(ex + ew), R(eye_y + eh)],
                  start=8, end=172, fill=BROW, width=R(5))
            continue

        h = eh if eye == 0 else int(eh * 0.42)
        lid = [P(ex - ew, eye_y + 2), P(ex - ew * 0.45, eye_y - h),
               P(ex + ew * 0.5, eye_y - h * 0.88), P(ex + ew, eye_y - 1)]
        d.polygon(lid + [P(ex + ew * 0.45, eye_y + h * 0.82),
                         P(ex - ew * 0.5, eye_y + h * 0.86)], fill=EYE_W)
        ir = int(h * 0.98) + 5
        ell(d, ex + sx * 2, eye_y, ir, ir, fill=IRIS)
        ell(d, ex + sx * 2, eye_y, ir * 0.44, ir * 0.44, fill=PUPIL)
        ell(d, ex + sx * 2 - ir * 0.32, eye_y - ir * 0.34, ir * 0.24, ir * 0.24,
            fill=(255, 255, 255))
        # 上睑线
        d.line(lid, fill=BROW, width=R(5), joint="curve")
        # 眼尾睫毛
        d.line([P(ex + sx * ew, eye_y - 1), P(ex + sx * (ew + 11), eye_y - 10)],
               fill=BROW, width=R(4))

    # 鼻子（只用极淡的鼻头阴影，避免出现“划痕”）
    nose = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    nd = ImageDraw.Draw(nose)
    ell(nd, cx + 2, hcy + 74, 15, 10, fill=SKIN_SH + (190,))
    nose = nose.filter(ImageFilter.GaussianBlur(R(4)))
    img = Image.alpha_composite(img, nose)
    d = ImageDraw.Draw(img)

    # 腮红（小、淡、位置偏高）
    blush = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush)
    for sx in (-1, 1):
        ell(bd, cx + sx * 76, hcy + 58, 27, 16, fill=BLUSH + (110,))
    blush = blush.filter(ImageFilter.GaussianBlur(R(11)))
    img = Image.alpha_composite(img, blush)
    d = ImageDraw.Draw(img)

    # ============================================================ 嘴部口型
    my = hcy + 112
    if mouth == 0:
        # 闭合微笑
        d.line([P(cx - 30, my - 3), P(cx, my + 8), P(cx + 30, my - 3)],
               fill=LIP, width=R(9), joint="curve")
        d.line([P(cx - 30, my - 3), P(cx, my + 8), P(cx + 30, my - 3)],
               fill=LIP_D, width=R(3), joint="curve")
    else:
        oh = {1: 8, 2: 14, 3: 20}[mouth]
        ow = {1: 26, 2: 28, 3: 26}[mouth]
        # 口腔
        ell(d, cx, my + 2, ow, oh, fill=MOUTH_IN)
        # 上排牙齿：只占口腔上部一条
        d.chord([R(cx - ow + 4), R(my + 2 - oh + 1),
                 R(cx + ow - 4), R(my + 2 + oh * 0.30)],
                start=180, end=360, fill=(250, 249, 246))
        # 唇形轮廓
        d.arc([R(cx - ow), R(my + 2 - oh), R(cx + ow), R(my + 2 + oh)],
              start=0, end=360, fill=LIP, width=R(5))

    # 下唇下方阴影
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    ell(sd, cx, my + 30, 26, 8, fill=SKIN_SH + (150,))
    sh = sh.filter(ImageFilter.GaussianBlur(R(6)))
    img = Image.alpha_composite(img, sh)

    return img.resize(CANVAS, Image.LANCZOS)


if __name__ == "__main__":
    combos = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 2), (2, 1)]
    sheet = Image.new("RGBA", (CANVAS[0] * len(combos), CANVAS[1]), (58, 62, 72, 255))
    for i, (m, e) in enumerate(combos):
        sheet.alpha_composite(render_person(m, e), (CANVAS[0] * i, 0))
    sheet.convert("RGB").resize((CANVAS[0] * len(combos) // 3, CANVAS[1] // 3),
                                Image.LANCZOS).save("assets/person_sheet.png")
    print("saved assets/person_sheet.png")
