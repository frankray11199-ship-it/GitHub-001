# -*- coding: utf-8 -*-
"""导出逐句讲稿，并生成一份可直接运行的 IndexTTS 批量合成脚本。

用途：在能访问 HuggingFace 的机器上用 IndexTTS（或任何别的工具）把 77 句
配音生成好，再拿回来喂给 `build.py --tts external`，画面、口型、字幕全部
按新音轨重新对齐。

用法:
    python export_lines.py                     # 导出到 build/lines/
    python export_lines.py --out D:/narration  # 导出到别处
"""

import argparse
import os

import script_content as sc
import tts_engine

BATCH_TEMPLATE = '''# -*- coding: utf-8 -*-
"""用 IndexTTS2 批量合成本片的 {n} 句旁白。

放到 index-tts 仓库根目录下运行。前置条件：
    git clone https://github.com/index-tts/index-tts && cd index-tts
    pip install -e .
    # 再把权重下到 checkpoints/（需要能访问 HuggingFace）
    huggingface-cli download IndexTeam/IndexTTS-2 --local-dir checkpoints

改下面两个路径，然后 python synth_indextts.py
"""

import os
import wave

REF_AUDIO = "examples/voice_07.wav"      # ← 换成你的参考人声（5~15 秒干净普通话）
OUT_DIR = r"{outdir}"                     # ← 生成的 wav 落到这里
CKPT = "checkpoints"

LINES = [
{lines}
]


def main():
    from indextts.infer_v2 import IndexTTS2

    os.makedirs(OUT_DIR, exist_ok=True)
    tts = IndexTTS2(cfg_path=os.path.join(CKPT, "config.yaml"),
                    model_dir=CKPT, use_fp16=False)

    sr0 = None
    for i, text in enumerate(LINES):
        out = os.path.join(OUT_DIR, "line_%03d.wav" % i)
        if os.path.exists(out):
            print("跳过已存在 %s" % out)
            continue
        tts.infer(spk_audio_prompt=REF_AUDIO, text=text,
                  output_path=out, verbose=False)
        with wave.open(out, "rb") as wf:
            sr = wf.getframerate()
        if sr0 is None:
            sr0 = sr
        elif sr != sr0:
            raise SystemExit("第 %d 句采样率 %d 与首句 %d 不一致" % (i, sr, sr0))
        print("[%d/%d] %s" % (i + 1, len(LINES), out))

    print("\\n全部完成，采样率 %s Hz。回到视频项目目录执行：" % sr0)
    print("  set TTS_EXTERNAL_DIR=%s" % OUT_DIR)
    print("  python build.py --tts external")


if __name__ == "__main__":
    main()
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("build", "lines"))
    ap.add_argument("--target", default="",
                    help="批量脚本里 wav 的落地目录，默认与 --out 同级的 external/")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    target = os.path.abspath(args.target) if args.target else \
        os.path.abspath(os.path.join("build", "audio", "external"))

    lines = sc.all_lines()

    # 逐句纯文本，方便手工核对或喂给别的工具
    for i, ln in enumerate(lines):
        with open(os.path.join(out, "line_%03d.txt" % i), "w", encoding="utf-8") as f:
            f.write(tts_engine.normalize_for_tts(ln["text"]))

    # 一份总表：序号 + 章节 + 文本
    with open(os.path.join(out, "lines.tsv"), "w", encoding="utf-8") as f:
        f.write("序号\t章节\t文本\n")
        for i, ln in enumerate(lines):
            ch = sc.CHAPTERS[ln["chapter"]]
            f.write("%03d\t%s\t%s\n" % (i, ch["title"], ln["text"]))

    # 可直接运行的 IndexTTS 批量脚本
    body = "\n".join('    %r,' % tts_engine.normalize_for_tts(ln["text"])
                     for ln in lines)
    script = BATCH_TEMPLATE.format(n=len(lines), lines=body,
                                   outdir=target.replace("\\", "\\\\"))
    sp = os.path.join(out, "synth_indextts.py")
    with open(sp, "w", encoding="utf-8") as f:
        f.write(script)

    print("已导出 %d 句到 %s" % (len(lines), out))
    print("  line_000.txt … line_%03d.txt   逐句文本" % (len(lines) - 1))
    print("  lines.tsv                      总表（序号/章节/文本）")
    print("  synth_indextts.py              IndexTTS 批量合成脚本")
    print("\n接下来：")
    print("  1. 把 synth_indextts.py 放到 index-tts 仓库根目录")
    print("  2. 改里面的 REF_AUDIO 指向你的参考人声，然后运行它")
    print("  3. 回到本项目：python build.py --tts external")


if __name__ == "__main__":
    main()
