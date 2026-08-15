# -*- coding: utf-8 -*-
"""下载中文 TTS 模型（跨平台，Windows / macOS / Linux 通用）。

这些模型由 k2-fsa/sherpa-onnx 转成 ONNX 后直接挂在 GitHub Release 上，
不经过 HuggingFace / ModelScope。

用法:
    python download_voices.py                # 只下默认引擎 melo 需要的模型
    python download_voices.py --engine all   # 四个引擎的模型全下
    python download_voices.py --dir D:/voices
"""

import argparse
import os
import sys
import tarfile
import urllib.request

SHERPA = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
PIPER = "https://github.com/rhasspy/piper/releases/download"

# 引擎 -> [(下载地址, 落地文件名, 解压后应存在的路径)]
ASSETS = {
    "melo": [
        (f"{SHERPA}/tts-models/vits-melo-tts-zh_en.tar.bz2",
         "vits-melo-tts-zh_en.tar.bz2", "vits-melo-tts-zh_en"),
    ],
    "kokoro": [
        (f"{SHERPA}/tts-models/kokoro-multi-lang-v1_0.tar.bz2",
         "kokoro-multi-lang-v1_0.tar.bz2", "kokoro-multi-lang-v1_0"),
    ],
    "matcha": [
        (f"{SHERPA}/tts-models/matcha-icefall-zh-baker.tar.bz2",
         "matcha-icefall-zh-baker.tar.bz2", "matcha-icefall-zh-baker"),
        (f"{SHERPA}/vocoder-models/vocos-22khz-univ.onnx",
         "vocos-22khz-univ.onnx", "vocos-22khz-univ.onnx"),
    ],
    "piper": [
        (f"{PIPER}/v0.0.2/voice-zh-cn-huayan-x-low.tar.gz",
         "voice-zh-cn-huayan-x-low.tar.gz", "zh-cn-huayan-x-low.onnx"),
    ],
}


def _hook(name):
    last = [-1]

    def report(blocks, bs, total):
        if total <= 0:
            return
        pct = min(100, blocks * bs * 100 // total)
        if pct == last[0]:          # 百分比没变就不刷新，否则会刷屏
            return
        last[0] = pct
        sys.stdout.write("\r  %-34s %3d%%  (%.0f MB)" % (name, pct, total / 1e6))
        sys.stdout.flush()
    return report


def _extract(path, dest):
    if not path.endswith((".tar.bz2", ".tar.gz")):
        return
    mode = "r:bz2" if path.endswith(".bz2") else "r:gz"
    with tarfile.open(path, mode) as tf:
        # Python 3.12+ 需要显式指定过滤器
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)


def download(engines, dest):
    os.makedirs(dest, exist_ok=True)
    names = []
    for e in engines:
        names.extend(ASSETS[e])

    for url, fname, produced in names:
        out_path = os.path.join(dest, produced)
        if os.path.exists(out_path):
            print("  %-34s 已存在，跳过" % produced)
            continue
        arch = os.path.join(dest, fname)
        if not os.path.exists(arch):
            urllib.request.urlretrieve(url, arch, _hook(fname))
            print()
        _extract(arch, dest)
        if arch != out_path and arch.endswith((".tar.bz2", ".tar.gz")):
            os.remove(arch)
        print("  %-34s 完成" % produced)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="melo",
                    choices=["melo", "kokoro", "matcha", "piper", "all"],
                    help="要下载哪个引擎的模型，默认只下 melo")
    ap.add_argument("--dir", default="voices", help="模型存放目录")
    args = ap.parse_args()

    engines = list(ASSETS) if args.engine == "all" else [args.engine]
    dest = os.path.abspath(args.dir)
    print("下载到:", dest)
    download(engines, dest)
    print("\n完成。构建前设置模型目录：")
    if os.name == "nt":
        print("  set TTS_MODEL_DIR=%s" % dest)
    else:
        print("  export TTS_MODEL_DIR=%s" % dest)


if __name__ == "__main__":
    main()
