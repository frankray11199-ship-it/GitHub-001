# -*- coding: utf-8 -*-
"""生成中文女声参考音频，用作 IndexTTS 等零样本音色克隆的音色样本。

为什么用合成音而不是网上找的真人录音：
  - 音色克隆会复制一个真实存在的人的声音，未经本人同意这样做并不合适；
  - 合成音不属于任何真人，没有授权问题；
  - 合成音干净、无底噪、无混响，恰恰是音色克隆最理想的参考素材。

用法:
    python make_reference.py                # 生成全部候选音色
    python make_reference.py --only melo    # 只生成某一个
"""

import argparse
import os
import wave

import numpy as np

import tts_engine

# 音素覆盖较全、语气自然的一段话，约 13 秒，适合做音色参考
REF_TEXT = (
    "您好，欢迎光临。我是前台接待员，很高兴为您服务。"
    "请问有什么可以帮您？办理入住需要出示您的有效证件。"
    "房价已包含次日早餐，退房时间是中午十二点。"
)

# (标签, 引擎, 说话人编号, 说明)
CANDIDATES = [
    ("melo",           "melo",   0,  "MeloTTS 中文女声，44.1kHz，本片当前配音"),
    ("kokoro_xiaobei", "kokoro", 46, "Kokoro zf_xiaobei，24kHz"),
    ("kokoro_xiaoni",  "kokoro", 47, "Kokoro zf_xiaoni，24kHz"),
    ("kokoro_xiaoxiao", "kokoro", 48, "Kokoro zf_xiaoxiao，24kHz"),
    ("kokoro_xiaoyi",  "kokoro", 49, "Kokoro zf_xiaoyi，24kHz"),
    ("matcha_baker",   "matcha", 0,  "Matcha 标贝女声，22.05kHz"),
]


def save_wav(path, samples, sr):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = float(np.abs(samples).max()) or 1.0
    a = (samples / peak * 0.92 * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(a.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/reference_voices")
    ap.add_argument("--only", default="", help="只生成指定标签")
    ap.add_argument("--speed", type=float, default=1.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    made = []
    for label, eng_name, sid, desc in CANDIDATES:
        if args.only and args.only != label:
            continue
        try:
            eng = tts_engine.get_engine(eng_name, args.speed)
            if hasattr(eng, "sid"):
                eng.sid = sid
            w = eng.synth(REF_TEXT)
            path = os.path.join(args.out, "%s.wav" % label)
            save_wav(path, w, eng.sample_rate)
            dur = len(w) / eng.sample_rate
            made.append((label, path, eng.sample_rate, dur, desc))
            print("  %-16s %5.1f 秒  %5d Hz  %s" % (label, dur, eng.sample_rate, desc))
        except SystemExit as e:
            print("  %-16s 跳过：%s" % (label, str(e).splitlines()[0]))
        except Exception as e:
            print("  %-16s 失败：%s" % (label, e))

    if made:
        print("\n共 %d 个候选音色，位于 %s" % (len(made), os.path.abspath(args.out)))
        print("挑一个作为 IndexTTS 的音色参考：")
        print("  set INDEXTTS_REF=%s\\<你选的>.wav" % os.path.abspath(args.out))
        print("  python build.py --tts indextts")


if __name__ == "__main__":
    main()
