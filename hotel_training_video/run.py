# -*- coding: utf-8 -*-
"""一键出片：检查环境 → 装依赖 → 下模型 → 渲染成片。

在自己电脑上只需要：
    python run.py

其它常用形式：
    python run.py --check              只体检，不下载不出片
    python run.py --quick              只渲染前 8 句，几分钟内看效果
    python run.py --tts kokoro         换配音引擎
    python run.py --no-install         不自动装 pip 依赖
"""

import argparse
import os
import subprocess
import sys

REQUIRED = [("PIL", "pillow"), ("numpy", "numpy")]
ENGINE_PKG = {"melo": "sherpa-onnx", "kokoro": "sherpa-onnx",
              "matcha": "sherpa-onnx", "piper": "piper-tts"}

HERE = os.path.dirname(os.path.abspath(__file__))

# Windows 控制台默认是 GBK 代码页，直接打印中文可能抛 UnicodeEncodeError，
# 这里强制把标准输出切成 UTF-8。
if os.name == "nt":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass



def missing_packages(engine):
    need = []
    for mod, pkg in REQUIRED:
        try:
            __import__(mod)
        except ImportError:
            need.append(pkg)
    mod = "sherpa_onnx" if ENGINE_PKG[engine] == "sherpa-onnx" else "piper"
    try:
        __import__(mod)
    except ImportError:
        need.append(ENGINE_PKG[engine])
    return need


def pip_install(pkgs):
    print("安装依赖:", " ".join(pkgs))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *pkgs])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts", default="melo",
                    choices=["melo", "kokoro", "matcha", "piper"])
    ap.add_argument("--speed", type=float, default=0.90)
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--voices", default=os.environ.get("TTS_MODEL_DIR")
                    or os.path.join(HERE, "voices"))
    ap.add_argument("--out", default=os.path.join(HERE, "output",
                                                  "酒店前厅部服务礼仪培训.mp4"))
    ap.add_argument("--check", action="store_true", help="只做环境体检")
    ap.add_argument("--quick", action="store_true", help="只渲染前 8 句")
    ap.add_argument("--no-install", action="store_true", help="不自动安装 pip 依赖")
    args = ap.parse_args()

    os.chdir(HERE)

    # ---------------------------------------------------------- 1. 依赖
    print("=" * 60)
    print("[1/4] 检查 Python 依赖")
    need = missing_packages(args.tts)
    if need:
        if args.no_install:
            raise SystemExit("缺少依赖: %s\n  请先运行: pip install %s"
                             % (" ".join(need), " ".join(need)))
        pip_install(need)
    print("      依赖齐全")

    # ---------------------------------------------------------- 2. 字体与 ffmpeg
    print("\n[2/4] 检查中文字体与 ffmpeg")
    try:
        import platform_support
    except ImportError:
        raise SystemExit("请在项目目录下运行 run.py")
    try:
        platform_support.ffmpeg_bin()
    except SystemExit:
        if args.no_install:
            raise
        pip_install(["imageio-ffmpeg"])
    platform_support.describe()

    if args.check:
        print("\n体检通过。执行 `python run.py` 即可出片。")
        return

    # ---------------------------------------------------------- 3. 模型
    print("\n[3/4] 准备配音模型")
    import download_voices
    download_voices.download([args.tts], args.voices)
    os.environ["TTS_MODEL_DIR"] = os.path.abspath(args.voices)

    # ---------------------------------------------------------- 4. 出片
    print("\n[4/4] 渲染成片")
    cmd = [sys.executable, "build.py", "--tts", args.tts,
           "--speed", str(args.speed), "--fps", str(args.fps), "--out", args.out]
    if args.quick:
        cmd += ["--limit", "8", "--out",
                os.path.join(HERE, "output", "_预览.mp4")]
    rc = subprocess.call(cmd, env=os.environ)
    if rc != 0:
        raise SystemExit("出片失败，返回码 %d" % rc)


if __name__ == "__main__":
    main()
