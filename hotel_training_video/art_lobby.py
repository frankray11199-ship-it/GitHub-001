# -*- coding: utf-8 -*-
"""程序化绘制酒店大堂（矢量风格插画）。

场景拆成三层，便于把角色夹在中间（人站在前台后面）：
    render_room()   房间层（天花板 / 背景墙 / 立柱 / 吊灯 / 地面 / 绿植）
    render_desk()   前台层（台体 / 台面 / 电脑 / 台灯），带透明通道
    apply_grade()   统一的灯光与暗角，在合成之后调用
"""

import math
import random

from PIL import Image, ImageDraw, ImageFilter

# ----------------------------------------------------------------- 调色板
C_CEIL_TOP = (32, 25, 20)
C_CEIL_BOT = (58, 44, 34)
C_WALL_TOP = (78, 58, 44)
C_WALL_BOT = (56, 41, 31)
C_PANEL = (92, 70, 52)
C_PANEL_D = (68, 50, 37)
C_GOLD = (206, 166, 86)
C_GOLD_L = (232, 205, 148)
C_MARBLE_T = (222, 210, 194)
C_MARBLE_B = (168, 152, 134)
C_DESK = (62, 44, 31)
C_DESK_D = (44, 31, 22)
C_DESK_TOP = (214, 200, 182)
C_PLANT = (46, 92, 66)
C_PLANT_D = (32, 68, 48)
C_GLOW = (255, 214, 150)

SS = 2                                  # 超采样倍数

# 画面关键水平线（相对高度）
R_CEIL = 0.30                           # 天花板 / 墙面
R_FLOOR = 0.62                          # 墙面 / 地面
R_DESK = 0.762                          # 前台台面


def _vgrad(size, top, bot):
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return img.resize((w, h), Image.BILINEAR)


def _screen(base, layer, amount=1.0):
    import numpy as np
    a = np.asarray(base.convert("RGB")).astype(np.float32) / 255.0
    b = np.asarray(layer).astype(np.float32) / 255.0 * amount
    out = 1.0 - (1.0 - a) * (1.0 - b)
    return Image.fromarray((out * 255).clip(0, 255).astype("uint8"))


# ===================================================================== 房间层
def render_room(width=1920, height=1080, seed=7):
    rnd = random.Random(seed)
    S = SS
    W, H = width * S, height * S
    y_ceil, y_floor = int(H * R_CEIL), int(H * R_FLOOR)
    cx = W // 2

    img = Image.new("RGB", (W, H), C_WALL_BOT)

    # ---------------------------------------------------------- 天花板
    img.paste(_vgrad((W, y_ceil), C_CEIL_TOP, C_CEIL_BOT), (0, 0))
    d = ImageDraw.Draw(img)
    for i in range(-3, 4):
        d.line([(cx + i * int(W * 0.16), 0), (cx + i * int(W * 0.23), y_ceil)],
               fill=(46, 36, 28), width=int(6 * S))
    for k in range(3):
        yy = int(y_ceil * (0.28 + k * 0.26))
        d.rectangle([int(W * 0.10), yy, int(W * 0.90), yy + int(7 * S)], fill=(120, 96, 66))

    # ---------------------------------------------------------- 背景墙
    img.paste(_vgrad((W, y_floor - y_ceil), C_WALL_TOP, C_WALL_BOT), (0, y_ceil))
    d = ImageDraw.Draw(img)
    pw = int(W * 0.075)
    for i in range(0, W // pw + 2):
        x = i * pw
        d.rectangle([x, y_ceil, x + pw - int(4 * S), y_floor],
                    fill=C_PANEL if i % 2 == 0 else C_PANEL_D)
        d.line([(x + pw - int(4 * S), y_ceil), (x + pw - int(4 * S), y_floor)],
               fill=(40, 29, 21), width=int(3 * S))
    d.rectangle([0, y_ceil, W, y_ceil + int(10 * S)], fill=C_GOLD)
    d.rectangle([0, y_ceil + int(10 * S), W, y_ceil + int(16 * S)], fill=(120, 92, 48))

    # 背景墙中央装饰壁板
    plate_w = int(W * 0.30)
    plate_h = int((y_floor - y_ceil) * 0.46)
    px0 = cx - plate_w // 2
    py0 = y_ceil + int((y_floor - y_ceil) * 0.18)
    d.rectangle([px0, py0, px0 + plate_w, py0 + plate_h], fill=(46, 34, 25))
    d.rectangle([px0, py0, px0 + plate_w, py0 + plate_h], outline=C_GOLD, width=int(3 * S))
    # 内嵌一圈细线脚，纯装饰、不含任何标识
    d.rectangle([px0 + int(18 * S), py0 + int(18 * S),
                 px0 + plate_w - int(18 * S), py0 + plate_h - int(18 * S)],
                outline=(126, 98, 54), width=int(2 * S))

    # ---------------------------------------------------------- 立柱
    for sx in (int(W * 0.085), int(W * 0.915)):
        cw = int(W * 0.055)
        d.rectangle([sx - cw // 2, y_ceil - int(20 * S), sx + cw // 2, y_floor], fill=(86, 65, 48))
        d.rectangle([sx - cw // 2, y_ceil - int(20 * S), sx - cw // 2 + int(10 * S), y_floor],
                    fill=(108, 83, 60))
        d.rectangle([sx + cw // 2 - int(8 * S), y_ceil - int(20 * S), sx + cw // 2, y_floor],
                    fill=(62, 46, 33))
        d.rectangle([sx - cw, y_ceil - int(28 * S), sx + cw, y_ceil + int(6 * S)], fill=C_GOLD)
        d.rectangle([sx - cw, y_floor - int(24 * S), sx + cw, y_floor], fill=(120, 92, 50))

    # ---------------------------------------------------------- 吊灯
    def chandelier(x, y, sc):
        rod_h = int(120 * S * sc)
        d.line([(x, 0), (x, y - rod_h // 2)], fill=(150, 120, 70), width=int(3 * S))
        yy = y - rod_h // 2
        for (rw, rh) in [(int(120 * S * sc), int(26 * S * sc)),
                         (int(84 * S * sc), int(22 * S * sc)),
                         (int(48 * S * sc), int(18 * S * sc))]:
            d.ellipse([x - rw, yy, x + rw, yy + rh * 2], outline=C_GOLD_L, width=int(3 * S))
            n = max(5, int(rw / (11 * S)))
            for i in range(n + 1):
                bx = x - rw + i * (2 * rw / n)
                by = yy + rh + int(math.sin(i * 1.1) * 4 * S)
                bl = int((16 + (i % 3) * 9) * S * sc)
                d.line([(bx, by), (bx, by + bl)], fill=(226, 198, 140), width=int(2 * S))
                d.ellipse([bx - int(3 * S), by + bl, bx + int(3 * S), by + bl + int(6 * S)],
                          fill=C_GOLD_L)
            yy += int(rh * 1.9)

    chandelier(cx, int(H * 0.20), 1.25)
    chandelier(int(W * 0.24), int(H * 0.16), 0.72)
    chandelier(int(W * 0.76), int(H * 0.16), 0.72)

    # ---------------------------------------------------------- 地面
    img.paste(_vgrad((W, H - y_floor), C_MARBLE_B, C_MARBLE_T), (0, y_floor))
    d = ImageDraw.Draw(img)
    for i in range(-9, 10):
        d.line([(cx + i * int(W * 0.075), y_floor), (cx + i * int(W * 0.30), H)],
               fill=(196, 182, 165), width=int(2 * S))
    yy, step = y_floor, int(14 * S)
    while yy < H:
        d.line([(0, yy), (W, yy)], fill=(198, 184, 167), width=int(2 * S))
        step = int(step * 1.34)
        yy += step

    refl = Image.new("RGB", (W, H), (0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for gx, gs in ((cx, 1.0), (int(W * 0.24), 0.6), (int(W * 0.76), 0.6)):
        rd.ellipse([gx - int(150 * S * gs), y_floor, gx + int(150 * S * gs), H],
                   fill=(int(120 * gs), int(96 * gs), int(60 * gs)))
    img = _screen(img, refl.filter(ImageFilter.GaussianBlur(70 * S // 2)), 0.55)
    d = ImageDraw.Draw(img)

    # ---------------------------------------------------------- 绿植
    def plant(x, ybase, sc):
        pw_ = int(70 * S * sc)
        ph_ = int(80 * S * sc)
        d.polygon([(x - pw_, ybase - ph_), (x + pw_, ybase - ph_),
                   (x + int(pw_ * 0.76), ybase), (x - int(pw_ * 0.76), ybase)], fill=(58, 48, 40))
        d.rectangle([x - pw_, ybase - ph_, x + pw_, ybase - ph_ + int(10 * S)], fill=(78, 66, 56))
        for i in range(13):
            ang = math.pi * (0.08 + 0.84 * i / 12)
            ln = int((150 + rnd.randint(-40, 60)) * S * sc)
            ex = x + int(math.cos(ang + math.pi) * ln * 0.85)
            ey = ybase - ph_ - int(math.sin(ang) * ln)
            col = C_PLANT if i % 2 == 0 else C_PLANT_D
            d.line([(x, ybase - ph_), (ex, ey)], fill=col, width=int(9 * S * sc))
            d.ellipse([ex - int(20 * S * sc), ey - int(13 * S * sc),
                       ex + int(20 * S * sc), ey + int(13 * S * sc)], fill=col)

    plant(int(W * 0.045), y_floor + int(H * 0.055), 1.05)
    plant(int(W * 0.955), y_floor + int(H * 0.055), 1.05)

    return img.resize((width, height), Image.LANCZOS)


# ===================================================================== 前台层
def render_desk(width=1920, height=1080):
    S = SS
    W, H = width * S, height * S
    y_desk = int(H * R_DESK)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    dx0, dx1 = int(W * 0.055), int(W * 0.945)
    d.rectangle([dx0, y_desk, dx1, H], fill=C_DESK + (255,))
    seg = int((dx1 - dx0) / 9)
    for i in range(9):
        x = dx0 + i * seg
        d.rectangle([x + int(8 * S), y_desk + int(46 * S), x + seg - int(8 * S), H],
                    fill=(C_DESK_D if i % 2 else (70, 50, 35)) + (255,))
    # 台面
    d.rectangle([dx0 - int(18 * S), y_desk - int(30 * S), dx1 + int(18 * S), y_desk + int(30 * S)],
                fill=C_DESK_TOP + (255,))
    d.rectangle([dx0 - int(18 * S), y_desk + int(24 * S), dx1 + int(18 * S), y_desk + int(34 * S)],
                fill=(150, 136, 118, 255))
    d.rectangle([dx0, y_desk + int(52 * S), dx1, y_desk + int(60 * S)], fill=(140, 108, 58, 255))

    # 台面陈设：电脑（右）、台灯（左）
    mx0 = int(W * 0.735)
    d.rectangle([mx0, y_desk - int(178 * S), mx0 + int(214 * S), y_desk - int(38 * S)],
                fill=(38, 40, 44, 255))
    d.rectangle([mx0 + int(10 * S), y_desk - int(168 * S), mx0 + int(204 * S), y_desk - int(48 * S)],
                fill=(70, 96, 118, 255))
    d.rectangle([mx0 + int(92 * S), y_desk - int(38 * S), mx0 + int(122 * S), y_desk - int(26 * S)],
                fill=(46, 48, 52, 255))

    lx = int(W * 0.135)
    d.polygon([(lx - int(52 * S), y_desk - int(112 * S)), (lx + int(52 * S), y_desk - int(112 * S)),
               (lx + int(34 * S), y_desk - int(176 * S)), (lx - int(34 * S), y_desk - int(176 * S))],
              fill=(206, 176, 120, 255))
    d.line([(lx, y_desk - int(112 * S)), (lx, y_desk - int(34 * S))],
           fill=(120, 92, 50, 255), width=int(7 * S))
    d.ellipse([lx - int(30 * S), y_desk - int(44 * S), lx + int(30 * S), y_desk - int(26 * S)],
              fill=(120, 92, 50, 255))

    return img.resize((width, height), Image.LANCZOS)


# ===================================================================== 灯光与暗角
_grade_cache = {}


def _grade_layers(W, H):
    """灯光与暗角只与画幅有关，缓存复用。"""
    if (W, H) in _grade_cache:
        return _grade_cache[(W, H)]
    cx = W // 2
    y_desk = int(H * R_DESK)

    spots = [
        (cx, int(H * 0.24), int(W * 0.16), 0.85),
        (int(W * 0.24), int(H * 0.19), int(W * 0.09), 0.55),
        (int(W * 0.76), int(H * 0.19), int(W * 0.09), 0.55),
        (int(W * 0.135), y_desk - int(150 * 0.5), int(W * 0.06), 0.55),
        (cx, int(H * R_CEIL) + int(H * 0.02), int(W * 0.34), 0.28),
    ]
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (x, y, r, a) in spots:
        gd.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v * a) for v in C_GLOW))
    glow = glow.filter(ImageFilter.GaussianBlur(70))

    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-int(W * 0.30), -int(H * 0.42), int(W * 1.30), int(H * 1.42)], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(150))

    _grade_cache[(W, H)] = (glow, vig, Image.new("RGB", (W, H), (14, 10, 8)))
    return _grade_cache[(W, H)]


def apply_grade(img, width=1920, height=1080):
    """在合成之后统一叠加灯光与暗角，让角色也融入场景光照。"""
    glow, vig, dark = _grade_layers(width, height)
    return Image.composite(_screen(img, glow, 0.70), dark, vig)


if __name__ == "__main__":
    room = render_room()
    desk = render_desk()
    comp = room.convert("RGBA")
    comp.alpha_composite(desk)
    apply_grade(comp.convert("RGB")).save("assets/lobby.png")
    room.save("assets/room.png")
    print("saved assets/lobby.png, assets/room.png")
