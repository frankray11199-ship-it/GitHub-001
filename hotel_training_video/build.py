# -*- coding: utf-8 -*-
"""成片构建：语音合成 → 时间轴 → 逐帧渲染 → ffmpeg 编码。

用法:
    python3 build.py [--fps 25] [--out output/前厅礼仪培训.mp4]
"""

import argparse
import logging
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image

import compose
import script_content as sc

logging.getLogger("piper").setLevel(logging.ERROR)
logging.getLogger("piper.phoneme_ids").setLevel(logging.CRITICAL)

VOICE = os.environ.get(
    "PIPER_VOICE",
    "/tmp/claude-0/-home-user-GitHub-001/2332cd09-79ee-518d-92c7-a50f3c8c225c/"
    "scratchpad/voices/zh-cn-huayan-x-low.onnx",
)
SR = 16000                      # piper 输出采样率

PAUSE_NORMAL = 0.34             # 句间停顿
PAUSE_CHAPTER_HEAD = 0.60       # 章节首句之后
PAUSE_CHAPTER_END = 0.95        # 章节末句之后
LEAD_IN = 1.0                   # 片头留白
LEAD_OUT = 2.0                  # 片尾留白

XFADE = 0.36                    # 版式切换时的交叉溶解时长（秒）


# ===================================================================== 语音
def synth_all(lines, cache="build/audio"):
    """逐句合成中文旁白，返回每句的 float32 波形。"""
    os.makedirs(cache, exist_ok=True)
    from piper import PiperVoice, SynthesisConfig

    voice = PiperVoice.load(VOICE)
    cfg = SynthesisConfig(length_scale=1.06, noise_scale=0.60,
                          noise_w_scale=0.75, normalize_audio=True)

    waves = []
    for i, ln in enumerate(lines):
        path = os.path.join(cache, "line_%03d.wav" % i)
        if not os.path.exists(path):
            with wave.open(path, "wb") as wf:
                voice.synthesize_wav(ln["text"], wf, syn_config=cfg)
        with wave.open(path, "rb") as wf:
            a = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        waves.append(a.astype(np.float32) / 32768.0)
        sys.stdout.write("\r  合成 %d/%d" % (i + 1, len(lines)))
        sys.stdout.flush()
    print()
    return waves


def build_timeline(lines, waves):
    """给每句排定起止时间，返回 (segments, 总时长, 完整音轨)。"""
    segs = []
    t = LEAD_IN
    for i, (ln, w) in enumerate(zip(lines, waves)):
        dur = len(w) / SR
        ch = sc.CHAPTERS[ln["chapter"]]
        last = (ln["index"] == len(ch["lines"]) - 1)
        first = (ln["index"] == 0)
        pause = (PAUSE_CHAPTER_END if last else
                 PAUSE_CHAPTER_HEAD if first else PAUSE_NORMAL)
        segs.append({"i": i, "line": ln, "start": t, "audio_end": t + dur,
                     "end": t + dur + pause, "wave": w})
        t += dur + pause
    total = t + LEAD_OUT

    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for s in segs:
        p = int(s["start"] * SR)
        track[p:p + len(s["wave"])] += s["wave"]
    peak = float(np.abs(track).max()) or 1.0
    track = track / peak * 0.89
    return segs, total, track


def write_wav(path, track):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((track * 32767).astype(np.int16).tobytes())


def write_srt(path, segs):
    def ts(t):
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        return "%02d:%02d:%02d,%03d" % (h, m, int(s), round((s - int(s)) * 1000))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for n, s in enumerate(segs, 1):
            f.write("%d\n%s --> %s\n%s\n\n" %
                    (n, ts(s["start"]), ts(s["end"]), s["line"]["text"]))


# ===================================================================== 口型
def mouth_track(seg, fps, total_frames_start):
    """按音频包络给出每帧口型，实现基本的口型同步。"""
    w = seg["wave"]
    n = int(round((seg["end"] - seg["start"]) * fps))
    out = []
    win = int(SR / fps)
    env = []
    for k in range(n):
        a, b = k * win, (k + 1) * win
        env.append(float(np.sqrt((w[a:b] ** 2).mean())) if a < len(w) else 0.0)
    mx = max(env) or 1.0
    for e in env:
        r = e / mx
        out.append(0 if r < 0.10 else 1 if r < 0.32 else 2 if r < 0.62 else 3)
    return out


def blink_frames(total_frames, fps, seed=11):
    """随机眨眼：返回每帧的眼睛状态。"""
    rnd = random.Random(seed)
    eyes = [0] * total_frames
    t = int(fps * 1.5)
    while t < total_frames - 4:
        for k, st in enumerate((1, 2, 2, 1)):
            if t + k < total_frames:
                eyes[t + k] = st
        t += int(fps * rnd.uniform(2.6, 5.4))
    return eyes


# ===================================================================== 版式
def plate_for(assets, seg, total):
    """按句子所属章节与位置选择版式，返回 (画面, 是否需要转场)。"""
    ln = seg["line"]
    ch = sc.CHAPTERS[ln["chapter"]]
    prog = seg["start"] / total
    idx = ln["index"]
    kind = ch["kind"]

    if kind == "opening" and idx <= 1:
        return compose.scene_title(assets, sc.VIDEO_TITLE, sc.VIDEO_SUBTITLE,
                                   ln["text"], 0, 0, prog), "title", idx == 0
    if kind == "closing" and idx == 0:
        return compose.scene_title(assets, ch["title"], ch["subtitle"],
                                   ln["text"], 0, 0, prog, big=False), "title", True
    if kind == "closing" and idx == len(ch["lines"]) - 1:
        return compose.scene_title(assets, "感谢观看", "把标准，做成习惯",
                                   ln["text"], 0, 0, prog, big=False), "title", True
    if kind == "chapter" and idx == 0:
        return compose.scene_chapter(assets, ch, ln["text"], 0, 0, prog), "chapter", True

    return compose.scene_main(assets, ch, ln["reveal"], ln["text"], 0, 0, prog), "main", idx <= 1


# ===================================================================== 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--out", default="output/酒店前厅部服务礼仪培训.mp4")
    ap.add_argument("--limit", type=int, default=0, help="只渲染前 N 句（调试用）")
    args = ap.parse_args()
    fps = args.fps

    lines = sc.all_lines()
    if args.limit:
        lines = lines[:args.limit]

    print("[1/5] 合成旁白 …")
    waves = synth_all(lines)

    print("[2/5] 排定时间轴 …")
    segs, total, track = build_timeline(lines, waves)
    write_wav("build/narration.wav", track)
    write_srt("output/酒店前厅部服务礼仪培训.srt", segs)
    print("      总时长 %.1f 秒（%.1f 分钟），共 %d 句" % (total, total / 60, len(segs)))

    print("[3/5] 准备美术资源 …")
    assets = compose.Assets()
    hb = compose.HEAD_BOX
    # 头部小块：正常 / 两档压暗，用于逐帧替换
    patches = {}
    for dim_name, alpha in (("main", 0.0), ("title", 0.48), ("chapter", 0.56)):
        for key, base in assets.bases.items():
            p = np.asarray(base.crop(hb)).astype(np.float32)
            if alpha:
                p = p * (1 - alpha) + np.array([8, 6, 5], dtype=np.float32) * alpha
            patches[(dim_name, key)] = p.astype(np.uint8)

    total_frames = int(round(total * fps))
    eyes = blink_frames(total_frames, fps)

    print("[4/5] 渲染 %d 帧并编码 …" % total_frames)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (compose.W, compose.H),
        "-r", str(fps), "-i", "-",
        "-i", "build/narration.wav",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
        "-c:a", "aac", "-b:a", "192k", "-shortest", args.out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    lead_frames = int(round(LEAD_IN * fps))
    xf = int(round(XFADE * fps))
    prev_arr = None
    frame_no = 0

    # 片头留白：用第一句的画面淡入
    first_plate, first_kind, _ = plate_for(assets, segs[0], total)
    first_arr = np.asarray(first_plate).astype(np.uint8)
    for k in range(lead_frames):
        t = min(1.0, k / max(1, lead_frames - 4))
        proc.stdin.write((first_arr.astype(np.float32) * t).astype(np.uint8).tobytes())
        frame_no += 1

    for si, seg in enumerate(segs):
        plate, kind, want_xf = (first_plate, first_kind, False) if si == 0 else \
            plate_for(assets, seg, total)
        arr = np.asarray(plate).astype(np.uint8)
        n = int(round(seg["end"] * fps)) - frame_no
        if n <= 0:
            continue
        mouths = mouth_track(seg, fps, frame_no)
        do_xf = want_xf and prev_arr is not None and si > 0

        for k in range(n):
            if do_xf and k < xf:
                t = (k + 1) / (xf + 1)
                cur = (prev_arr.astype(np.float32) * (1 - t) +
                       arr.astype(np.float32) * t).astype(np.uint8)
            else:
                cur = arr.copy()
            m = mouths[k] if k < len(mouths) else 0
            e = eyes[min(frame_no, total_frames - 1)]
            cur[hb[1]:hb[3], hb[0]:hb[2]] = patches[(kind, (m, e))]
            proc.stdin.write(cur.tobytes())
            frame_no += 1
            if frame_no % 250 == 0:
                sys.stdout.write("\r      %d/%d 帧 (%.0f%%)" %
                                 (frame_no, total_frames, 100.0 * frame_no / total_frames))
                sys.stdout.flush()
        prev_arr = arr

    # 片尾留白：淡出
    tail = max(0, total_frames - frame_no)
    for k in range(tail):
        t = max(0.0, 1.0 - k / max(1, tail - 4))
        proc.stdin.write((prev_arr.astype(np.float32) * t).astype(np.uint8).tobytes())
    print()

    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise SystemExit("ffmpeg 失败，返回码 %d" % rc)

    print("[5/5] 完成 →", args.out)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration,size", "-of", "default=nw=1", args.out],
                         capture_output=True, text=True).stdout
    print(out.strip())


if __name__ == "__main__":
    main()
