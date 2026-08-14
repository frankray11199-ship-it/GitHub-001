# -*- coding: utf-8 -*-
"""中文旁白合成引擎（可插拔）。

默认使用 sherpa-onnx 上的 MeloTTS 中文模型（44.1kHz），
它把 MeloTTS 转成了 ONNX 并**直接托管在 GitHub Release**，
不依赖 HuggingFace / ModelScope，便于在受限网络里获取。

    get_engine("melo")    MeloTTS  44100Hz  中文，音质最好，默认
    get_engine("kokoro")  Kokoro   24000Hz  多语种
    get_engine("matcha")  Matcha   22050Hz  合成最快（实时率 3x+）
    get_engine("piper")   Piper    16000Hz  体积最小

模型目录由环境变量 TTS_MODEL_DIR 指定，默认 ./voices。
下载方式见 download_voices.sh。
"""

import os

import numpy as np

MODEL_DIR = os.environ.get("TTS_MODEL_DIR", "voices")

# TTS 读不出来的标点，换成停顿含义相近的符号（只影响朗读，不影响字幕）
_PUNCT_FIX = {"：": "，", "；": "，", "…": "。", "——": "，", "、": "，"}


def normalize_for_tts(text):
    for a, b in _PUNCT_FIX.items():
        text = text.replace(a, b)
    return text


class _SherpaEngine:
    def __init__(self, name, config, sid=0, speed=1.0):
        import sherpa_onnx
        self.name = name
        self.sid = sid
        self.speed = speed
        self.tts = sherpa_onnx.OfflineTts(config)
        self.sample_rate = self.tts.sample_rate

    def synth(self, text):
        a = self.tts.generate(normalize_for_tts(text), sid=self.sid, speed=self.speed)
        return np.asarray(a.samples, dtype=np.float32)


def _melo(speed):
    import sherpa_onnx
    d = os.path.join(MODEL_DIR, "vits-melo-tts-zh_en")
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=f"{d}/model.onnx", lexicon=f"{d}/lexicon.txt",
                tokens=f"{d}/tokens.txt", dict_dir=f"{d}/dict"),
            provider="cpu", num_threads=4),
        rule_fsts=",".join([f"{d}/date.fst", f"{d}/number.fst", f"{d}/phone.fst"]),
        max_num_sentences=1)
    return _SherpaEngine("melo", cfg, sid=0, speed=speed)


def _kokoro(speed):
    import sherpa_onnx
    d = os.path.join(MODEL_DIR, "kokoro-multi-lang-v1_0")
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=f"{d}/model.onnx", voices=f"{d}/voices.bin",
                tokens=f"{d}/tokens.txt", data_dir=f"{d}/espeak-ng-data",
                dict_dir=f"{d}/dict",
                lexicon=f"{d}/lexicon-zh.txt,{d}/lexicon-us-en.txt"),
            provider="cpu", num_threads=4),
        max_num_sentences=1)
    return _SherpaEngine("kokoro", cfg, sid=47, speed=speed)


def _matcha(speed):
    import sherpa_onnx
    d = os.path.join(MODEL_DIR, "matcha-icefall-zh-baker")
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=f"{d}/model-steps-3.onnx",
                vocoder=os.path.join(MODEL_DIR, "vocos-22khz-univ.onnx"),
                lexicon=f"{d}/lexicon.txt", tokens=f"{d}/tokens.txt",
                dict_dir=f"{d}/dict"),
            provider="cpu", num_threads=4),
        rule_fsts=",".join([f"{d}/date.fst", f"{d}/number.fst", f"{d}/phone.fst"]),
        max_num_sentences=1)
    return _SherpaEngine("matcha", cfg, sid=0, speed=speed)


class _PiperEngine:
    """保留 piper 作为最小体积的兜底方案。"""

    def __init__(self, speed):
        import logging
        logging.getLogger("piper").setLevel(logging.CRITICAL)
        logging.getLogger("piper.phoneme_ids").setLevel(logging.CRITICAL)
        from piper import PiperVoice, SynthesisConfig
        self.name = "piper"
        self.voice = PiperVoice.load(os.path.join(MODEL_DIR, "zh-cn-huayan-x-low.onnx"))
        self.cfg = SynthesisConfig(length_scale=1.0 / speed, noise_scale=0.60,
                                   noise_w_scale=0.75, normalize_audio=True)
        self.sample_rate = 16000

    def synth(self, text):
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            self.voice.synthesize_wav(normalize_for_tts(text), wf, syn_config=self.cfg)
        buf.seek(0)
        with wave.open(buf, "rb") as wf:
            self.sample_rate = wf.getframerate()
            a = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        return a.astype(np.float32) / 32768.0


_ENGINES = {"melo": _melo, "kokoro": _kokoro, "matcha": _matcha,
            "piper": lambda speed: _PiperEngine(speed)}


def get_engine(name="melo", speed=0.90):
    """speed < 1 更慢、更适合培训讲解。"""
    if name not in _ENGINES:
        raise SystemExit("未知引擎 %r，可选: %s" % (name, ", ".join(_ENGINES)))
    return _ENGINES[name](speed)
