# -*- coding: utf-8 -*-
"""画面合成：把大堂、角色、要点板、字幕组装成 1920×1080 的成片画面。"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import art_lobby
import art_person

W, H = 1920, 1080

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_PATH_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_INDEX = 2                      # NotoSansCJK 中的简体中文字面

GOLD = (208, 170, 96)
GOLD_L = (238, 212, 156)
CREAM = (245, 241, 233)
DIM = (150, 142, 130)

_font_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        path = FONT_PATH_B if bold else FONT_PATH
        _font_cache[key] = ImageFont.truetype(path, size, index=FONT_INDEX)
    return _font_cache[key]


# --------------------------------------------------------------- 文本工具
def text_w(d, s, f):
    return d.textbbox((0, 0), s, font=f)[2]


# 避头尾：这些标点不能出现在行首
NO_LINE_START = "。，、；：？！）〕】》」』…·%"


def wrap_cjk(d, s, f, max_w):
    """按像素宽度对中文断行，并遵守避头尾规则。"""
    lines, cur = [], ""
    for ch in s:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        # 标点宁可略微出格，也不单独落到下一行行首
        if text_w(d, cur + ch, f) > max_w and cur and ch not in NO_LINE_START:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def draw_text_sh(d, xy, s, f, fill, shadow=(0, 0, 0, 170), off=3, anchor=None):
    x, y = xy
    d.text((x + off, y + off), s, font=f, fill=shadow, anchor=anchor)
    d.text((x, y), s, font=f, fill=fill, anchor=anchor)


# --------------------------------------------------------------- 静态资源
class Assets:
    """一次性渲染并缓存所有静态图层与角色变体。"""

    def __init__(self, cache_dir="assets"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        self.room = self._cached("room.png", lambda: art_lobby.render_room(W, H))
        self.desk = self._cached("desk.png", lambda: art_lobby.render_desk(W, H), rgba=True)

        # 角色变体：4 种口型 × 3 种眼睛
        self.person = {}
        pw, ph = art_person.CANVAS
        scale = 0.70
        self.p_size = (int(pw * scale), int(ph * scale))
        self.p_pos = (94, 137)
        for m in range(4):
            for e in range(3):
                name = "person_m%d_e%d.png" % (m, e)
                im = self._cached(name, lambda m=m, e=e: art_person.render_person(m, e), rgba=True)
                self.person[(m, e)] = im.resize(self.p_size, Image.LANCZOS)

        # 12 种表情各预合成一张完整场景（房间 + 角色 + 前台 + 光照）。
        # 它们彼此只在头部区域不同，逐帧动画时只需搬运 HEAD_BOX 这一小块。
        self.bases = {}
        for key, ppl in self.person.items():
            base = self.room.convert("RGBA")
            base.alpha_composite(ppl, self.p_pos)
            base.alpha_composite(self.desk)
            self.bases[key] = art_lobby.apply_grade(base.convert("RGB"), W, H)

    def _cached(self, name, fn, rgba=False):
        path = os.path.join(self.cache_dir, name)
        if os.path.exists(path):
            return Image.open(path).convert("RGBA" if rgba else "RGB")
        im = fn()
        im.save(path)
        return im.convert("RGBA" if rgba else "RGB")


# --------------------------------------------------------------- 图层绘制
def _panel(d, box, radius=22, fill=(20, 15, 12, 214), border=GOLD, bw=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=border + (235,), width=bw)


# 片头 / 章节卡的文字水平中心（避开左侧角色）
TEXT_CX = 1180

# 头部外接框（帧动画时只重绘这一块）
HEAD_BOX = (322, 236, 540, 496)


def _scene_base(assets, mouth=0, eye=0):
    return assets.bases[(mouth, eye)]


def _overlay_dim(img, alpha):
    ov = Image.new("RGBA", (W, H), (8, 6, 5, int(255 * alpha)))
    out = img.convert("RGBA")
    out.alpha_composite(ov)
    return out


# --------------------------------------------------------------- 各类版式
def draw_progress(d, ratio):
    """底部进度条。"""
    d.rectangle([0, H - 7, W, H], fill=(30, 24, 20, 200))
    d.rectangle([0, H - 7, int(W * ratio), H], fill=GOLD)


def draw_subtitle(img, text):
    """底部字幕条。"""
    d = ImageDraw.Draw(img, "RGBA")
    f = font(42, True)
    lines = wrap_cjk(d, text, f, W - 360)[:2]
    bar_h = 74 + 56 * (len(lines) - 1)
    y0 = H - 34 - bar_h
    grad = Image.new("RGBA", (W, bar_h + 60), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(bar_h + 60):
        a = int(150 * min(1.0, i / 40.0))
        gd.line([(0, i), (W, i)], fill=(8, 6, 5, a))
    img.alpha_composite(grad, (0, y0 - 30))
    d = ImageDraw.Draw(img, "RGBA")
    for i, ln in enumerate(lines):
        draw_text_sh(d, (W // 2, y0 + 30 + i * 56), ln, f, CREAM, anchor="mm")


def scene_main(assets, ch, reveal, subtitle, mouth, eye, progress):
    """主版式：左角色 + 右要点板 + 字幕。"""
    img = _scene_base(assets, mouth, eye).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    px0, py0, px1 = 892, 132, 1852
    items = ch["items"]
    row_h = 74
    py1 = py0 + 132 + row_h * len(items)
    _panel(d, [px0, py0, px1, py1])

    # 标题栏
    d.rectangle([px0 + 2, py0 + 2, px1 - 2, py0 + 96], fill=(GOLD[0], GOLD[1], GOLD[2], 34))
    if ch["no"]:
        d.rounded_rectangle([px0 + 26, py0 + 24, px0 + 90, py0 + 76], radius=8, fill=GOLD + (255,))
        d.text((px0 + 58, py0 + 50), str(ch["no"]), font=font(38, True),
               fill=(26, 20, 16), anchor="mm")
        tx = px0 + 110
    else:
        tx = px0 + 34
    d.text((tx, py0 + 50), ch["panel"], font=font(40, True), fill=GOLD_L, anchor="lm")

    # 条目（逐条亮起）
    f_item = font(33)
    for i, it in enumerate(items):
        y = py0 + 132 + i * row_h + row_h // 2
        if i < reveal:
            new = (i == reveal - 1)
            col = (255, 255, 255) if new else CREAM
            mk = GOLD_L if new else GOLD
            d.polygon([(px0 + 46, y), (px0 + 57, y - 11), (px0 + 68, y), (px0 + 57, y + 11)],
                      fill=mk)
            d.text((px0 + 90, y), it, font=f_item, fill=col, anchor="lm")
            if new:
                d.rounded_rectangle([px0 + 26, y - 30, px1 - 26, y + 30], radius=8,
                                    fill=(GOLD[0], GOLD[1], GOLD[2], 26))
                d.polygon([(px0 + 46, y), (px0 + 57, y - 11), (px0 + 68, y), (px0 + 57, y + 11)],
                          fill=mk)
                d.text((px0 + 90, y), it, font=f_item, fill=col, anchor="lm")
        else:
            d.polygon([(px0 + 48, y), (px0 + 57, y - 9), (px0 + 66, y), (px0 + 57, y + 9)],
                      fill=(90, 84, 76))
            d.text((px0 + 90, y), it, font=f_item, fill=(96, 90, 82), anchor="lm")

    draw_subtitle(img, subtitle)
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, progress)
    return img.convert("RGB")


def scene_title(assets, title, subtitle, caption, mouth, eye, progress, big=True):
    """片头 / 结语版式：压暗场景 + 居中大标题。"""
    img = _overlay_dim(_scene_base(assets, mouth, eye), 0.48)
    d = ImageDraw.Draw(img, "RGBA")

    tcx = TEXT_CX
    cy = 366
    f_t = font(88 if big else 78, True)
    lines = wrap_cjk(d, title, f_t, W - 860)
    for i, ln in enumerate(lines):
        draw_text_sh(d, (tcx, cy + i * 112), ln, f_t, CREAM, off=4, anchor="mm")
    y = cy + len(lines) * 112 - 40

    d.line([(tcx - 180, y + 40), (tcx + 180, y + 40)], fill=GOLD, width=3)
    d.polygon([(tcx - 14, y + 40), (tcx, y + 26), (tcx + 14, y + 40),
               (tcx, y + 54)], fill=GOLD_L)
    d.text((tcx, y + 108), subtitle, font=font(42), fill=GOLD_L, anchor="mm")

    if caption:
        draw_subtitle(img, caption)
        d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, progress)
    return img.convert("RGB")


def scene_chapter(assets, ch, caption, mouth, eye, progress):
    """章节卡：大号章节序号 + 标题。"""
    img = _overlay_dim(_scene_base(assets, mouth, eye), 0.56)
    d = ImageDraw.Draw(img, "RGBA")

    tcx = TEXT_CX
    d.text((tcx, 292), "第 %d 讲" % ch["no"], font=font(46, True), fill=GOLD, anchor="mm")
    draw_text_sh(d, (tcx, 400), ch["title"], font(96, True), CREAM, off=4, anchor="mm")
    d.line([(tcx - 200, 486), (tcx + 200, 486)], fill=GOLD, width=3)
    d.text((tcx, 552), ch["subtitle"], font=font(42), fill=GOLD_L, anchor="mm")

    draw_subtitle(img, caption)
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, progress)
    return img.convert("RGB")
