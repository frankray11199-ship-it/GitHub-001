#!/usr/bin/env bash
# 下载中文 TTS 模型。
#
# 这些模型都由 k2-fsa/sherpa-onnx 转成 ONNX 后**直接挂在 GitHub Release** 上，
# 不经过 HuggingFace / ModelScope，因此在只放行 github.com 的网络里也能取到。
#
# 用法:  bash download_voices.sh [目标目录]     默认 ./voices
set -euo pipefail

DIR="${1:-voices}"
mkdir -p "$DIR"
cd "$DIR"

SHERPA=https://github.com/k2-fsa/sherpa-onnx/releases/download

fetch() {  # fetch <url> <落地文件名>
  [ -e "$2" ] && { echo "已存在，跳过: $2"; return; }
  echo "下载 $2 …"
  curl -sSL --retry 4 --retry-delay 2 -o "$2" "$1"
}

# MeloTTS 中文（44.1kHz，默认使用，音质最好）
fetch "$SHERPA/tts-models/vits-melo-tts-zh_en.tar.bz2" vits-melo-tts-zh_en.tar.bz2

# Kokoro 多语种（24kHz）
fetch "$SHERPA/tts-models/kokoro-multi-lang-v1_0.tar.bz2" kokoro-multi-lang-v1_0.tar.bz2

# Matcha 中文标贝（22.05kHz，合成最快，需配 vocoder）
fetch "$SHERPA/tts-models/matcha-icefall-zh-baker.tar.bz2" matcha-icefall-zh-baker.tar.bz2
fetch "$SHERPA/vocoder-models/vocos-22khz-univ.onnx" vocos-22khz-univ.onnx

# Piper 中文（16kHz，兜底方案，体积最小）
fetch "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-zh-cn-huayan-x-low.tar.gz" \
      voice-zh-cn-huayan-x-low.tar.gz

for f in *.tar.bz2; do [ -e "$f" ] && tar xjf "$f"; done
for f in *.tar.gz;  do [ -e "$f" ] && tar xzf "$f"; done

echo
echo "完成。构建时指定模型目录："
echo "  export TTS_MODEL_DIR=$(pwd)"
echo "  python3 build.py --tts melo"
