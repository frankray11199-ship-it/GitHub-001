# -*- coding: utf-8 -*-
"""跨平台支持：中文字体查找与 ffmpeg 定位。

Windows / macOS / Linux 上字体路径和 ffmpeg 位置都不一样，
这里统一探测，避免在别人机器上一跑就报"找不到字体"。

可用环境变量强制指定：
    CJK_FONT / CJK_FONT_BOLD   中文字体文件路径
    CJK_FONT_INDEX / CJK_FONT_BOLD_INDEX   ttc 字体集合内的字面序号
    FFMPEG / FFPROBE           可执行文件路径
"""

import os
import shutil
import subprocess
import sys

from PIL import ImageFont

# (常规字体, 序号, 粗体, 序号)。粗体缺失时用 None，回退到常规。
_FONT_CANDIDATES = [
    # ---------------------------------------------------------- Linux
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2,
     "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 2),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0,
     "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-VF.otf.ttc", 2, None, 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0, None, 0),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", 0, None, 0),
    # ---------------------------------------------------------- Windows
    ("C:/Windows/Fonts/msyh.ttc", 0, "C:/Windows/Fonts/msyhbd.ttc", 0),     # 微软雅黑
    ("C:/Windows/Fonts/msyh.ttf", 0, "C:/Windows/Fonts/msyhbd.ttf", 0),
    ("C:/Windows/Fonts/simhei.ttf", 0, None, 0),                            # 黑体
    ("C:/Windows/Fonts/simsun.ttc", 0, None, 0),                            # 宋体
    ("C:/Windows/Fonts/Deng.ttf", 0, "C:/Windows/Fonts/Dengb.ttf", 0),      # 等线
    # ---------------------------------------------------------- macOS
    ("/System/Library/Fonts/PingFang.ttc", 2, "/System/Library/Fonts/PingFang.ttc", 4),
    ("/System/Library/Fonts/PingFang.ttc", 0, None, 0),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0, None, 0),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0, None, 0),
    ("/Library/Fonts/Arial Unicode.ttf", 0, None, 0),
]

_PROBE_TEXT = "礼仪前厅"          # 用真实汉字验证字体确实有中文字形


def _usable(path, index):
    """能加载、且能画出中文字形，才算可用。"""
    if not path or not os.path.exists(path):
        return False
    try:
        f = ImageFont.truetype(path, 48, index=index)
        bbox = f.getbbox(_PROBE_TEXT)
    except Exception:
        return False
    # 缺字形时 PIL 会画成空白或豆腐块，宽度会明显偏小
    return bbox is not None and (bbox[2] - bbox[0]) > 48 * len(_PROBE_TEXT) * 0.5


def _fc_match():
    """Linux 下问 fontconfig 要一个中文字体。"""
    if not shutil.which("fc-match"):
        return None
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", ":lang=zh-cn"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out or None
    except Exception:
        return None


def find_cjk_fonts():
    """返回 ((常规字体路径, 序号), (粗体路径, 序号))。找不到就报错并给出安装提示。"""
    env_r = os.environ.get("CJK_FONT")
    if env_r:
        ri = int(os.environ.get("CJK_FONT_INDEX", "0"))
        bp = os.environ.get("CJK_FONT_BOLD", env_r)
        bi = int(os.environ.get("CJK_FONT_BOLD_INDEX", str(ri)))
        if not _usable(env_r, ri):
            raise SystemExit("CJK_FONT 指定的字体不可用: %s" % env_r)
        return (env_r, ri), (bp if _usable(bp, bi) else env_r, bi if _usable(bp, bi) else ri)

    for (rp, ri, bp, bi) in _FONT_CANDIDATES:
        if _usable(rp, ri):
            if bp and _usable(bp, bi):
                return (rp, ri), (bp, bi)
            return (rp, ri), (rp, ri)

    fb = _fc_match()
    if fb and _usable(fb, 0):
        return (fb, 0), (fb, 0)

    raise SystemExit(
        "找不到可用的中文字体。请安装任一中文字体后重试：\n"
        "  Windows : 系统自带微软雅黑，通常无需安装；若报此错请设 CJK_FONT 指向字体文件\n"
        "  macOS   : 系统自带苹方，通常无需安装\n"
        "  Ubuntu  : sudo apt-get install -y fonts-noto-cjk\n"
        "  其他    : 下载思源黑体后设 CJK_FONT=/path/to/SourceHanSansSC-Regular.otf")


def ffmpeg_bin():
    """优先用 PATH 里的 ffmpeg，没有就用 imageio-ffmpeg 自带的那份。"""
    env = os.environ.get("FFMPEG")
    if env:
        return env
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit(
            "找不到 ffmpeg。任选其一：\n"
            "  pip install imageio-ffmpeg        （最省事，自带一份可执行文件）\n"
            "  Windows : winget install Gyan.FFmpeg\n"
            "  macOS   : brew install ffmpeg\n"
            "  Ubuntu  : sudo apt-get install -y ffmpeg")


def ffprobe_bin():
    """ffprobe 只用来打印成片信息，缺了不影响出片。"""
    return os.environ.get("FFPROBE") or shutil.which("ffprobe")


def describe():
    (rp, ri), (bp, bi) = find_cjk_fonts()
    print("平台      :", sys.platform)
    print("Python    :", sys.version.split()[0])
    print("中文字体  : %s (index=%d)" % (rp, ri))
    print("粗体      : %s (index=%d)" % (bp, bi))
    print("ffmpeg    :", ffmpeg_bin())
    print("ffprobe   :", ffprobe_bin() or "（未找到，不影响出片）")


if __name__ == "__main__":
    describe()
