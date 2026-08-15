# -*- coding: utf-8 -*-
"""中文旁白合成引擎（可插拔）。

默认使用 sherpa-onnx 上的 MeloTTS 中文模型（44.1kHz），
它把 MeloTTS 转成了 ONNX 并**直接托管在 GitHub Release**，
不依赖 HuggingFace / ModelScope，便于在受限网络里获取。

    get_engine("melo")    MeloTTS  44100Hz  中文，音质最好，默认
    get_engine("kokoro")  Kokoro   24000Hz  多语种
    get_engine("matcha")  Matcha   22050Hz  合成最快（实时率 3x+）
    get_engine("piper")   Piper    16000Hz  体积最小

另有两个不依赖 sherpa-onnx 的引擎：

    get_engine("indextts")  IndexTTS2 零样本音色克隆。需要能访问 HuggingFace，
                            并用 INDEXTTS_REF 指定一段参考音频决定音色。
    get_engine("external")  不合成，直接读取事先备好的逐句 wav，
                            用于把任意外部工具生成的配音接进来。

模型目录由环境变量 TTS_MODEL_DIR 指定，默认 ./voices。
下载方式见 download_voices.py。
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


class _IndexTTSEngine:
    """IndexTTS2 零样本音色克隆。

    需要三样东西，缺一不可：
      1. clone 官方仓库并 pip install -e .（pypi 上没有这个包）
      2. checkpoints/ 下的权重，只在 HuggingFace / ModelScope 上有
      3. INDEXTTS_REF 指向一段参考音频（决定合成出来的音色）

    输出采样率不写死，用一句探针实测后再上报，避免猜错导致时间轴错位。
    """

    def __init__(self, speed):
        import wave as _wave

        ref = os.environ.get("INDEXTTS_REF")
        if not ref or not os.path.exists(ref):
            raise SystemExit(
                "IndexTTS 需要一段参考音频来决定音色，请先设置：\n"
                "  INDEXTTS_REF=/path/to/参考人声.wav\n"
                "建议 5~15 秒、干净无背景音、与目标风格接近的普通话录音。")
        self.name = "indextts"
        self.ref = ref
        self.speed = speed
        self._wave = _wave
        self._tmp = os.path.join("build", "audio", "_indextts_tmp.wav")
        os.makedirs(os.path.dirname(self._tmp), exist_ok=True)

        ckpt = os.environ.get("INDEXTTS_CKPT", "checkpoints")
        try:
            from indextts.infer_v2 import IndexTTS2
        except ImportError:
            raise SystemExit(
                "没找到 indextts 模块。pypi 上没有这个包，需要从源码装：\n"
                "  git clone https://github.com/index-tts/index-tts\n"
                "  cd index-tts && pip install -e .\n"
                "然后把权重下到 checkpoints/（需要能访问 HuggingFace）。")
        self.tts = IndexTTS2(cfg_path=os.path.join(ckpt, "config.yaml"),
                             model_dir=ckpt, use_fp16=False)

        self.sample_rate = self._probe()

    def _run(self, text):
        self.tts.infer(spk_audio_prompt=self.ref, text=normalize_for_tts(text),
                       output_path=self._tmp, verbose=False)
        with self._wave.open(self._tmp, "rb") as wf:
            sr = wf.getframerate()
            ch = wf.getnchannels()
            a = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        a = a.astype(np.float32) / 32768.0
        if ch > 1:
            a = a.reshape(-1, ch).mean(axis=1)
        return sr, a

    def _probe(self):
        sr, _ = self._run("您好，欢迎光临。")
        return sr

    def synth(self, text):
        return self._run(text)[1]


class _ExternalEngine:
    """不做合成，直接读用户事先备好的逐句 wav。

    把 line_000.wav … line_076.wav 放进 build/audio/external/（或
    TTS_EXTERNAL_DIR 指定的目录），就能把任何外部工具生成的配音接进流水线，
    时间轴、口型同步、字幕都照常重新计算。
    """

    name = "external"

    def __init__(self, speed):
        import wave as _wave
        self._wave = _wave
        self.dir = os.environ.get("TTS_EXTERNAL_DIR",
                                  os.path.join("build", "audio", "external"))
        if not os.path.isdir(self.dir):
            raise SystemExit("外部配音目录不存在: %s\n"
                             "请先把逐句 wav 放进去，命名为 line_000.wav 起。" % self.dir)
        first = os.path.join(self.dir, "line_000.wav")
        if not os.path.exists(first):
            raise SystemExit("%s 里缺少 line_000.wav" % self.dir)
        with self._wave.open(first, "rb") as wf:
            self.sample_rate = wf.getframerate()

    def synth(self, text):
        raise SystemExit(
            "external 引擎不做合成。请确认 %s 下每一句的 wav 都齐全"
            "（共 77 句，line_000.wav … line_076.wav），"
            "且采样率一致。用 export_lines.py 可以导出每句的文本。" % self.dir)


_ENGINES = {"melo": _melo, "kokoro": _kokoro, "matcha": _matcha,
            "piper": lambda speed: _PiperEngine(speed),
            "indextts": lambda speed: _IndexTTSEngine(speed),
            "external": lambda speed: _ExternalEngine(speed)}


def get_engine(name="melo", speed=0.90):
    """speed < 1 更慢、更适合培训讲解。"""
    if name not in _ENGINES:
        raise SystemExit("未知引擎 %r，可选: %s" % (name, ", ".join(_ENGINES)))
    return _ENGINES[name](speed)
