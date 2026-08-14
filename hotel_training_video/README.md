# 酒店前厅部服务礼仪培训视频

一套**全部由代码生成**的中文培训视频：程序化绘制酒店大堂与前台接待员角色，
离线合成中文旁白，逐帧渲染并编码为 1080p MP4。

## 成片

| | |
|---|---|
| 文件 | `output/酒店前厅部服务礼仪培训.mp4` |
| 时长 | 8 分 24 秒 |
| 规格 | 1920×1080 · 25fps · H.264 / AAC 48kHz |
| 配音 | MeloTTS 中文离线神经 TTS（44.1kHz 合成） |
| 字幕 | 画面内嵌，同时另附 `output/酒店前厅部服务礼仪培训.srt` |

## 内容结构

片头 + 七讲 + 结语，共 77 句旁白：

1. **仪容仪表** —— 制服、工牌、发型、妆容、手部、饰品、鞋袜
2. **仪态与微笑** —— 站姿、微笑、目光、手势
3. **迎宾问候与服务用语** —— 迎候、询问、致歉、应答、道别、服务禁语、首问负责制
4. **入住登记标准流程** —— 七步法，从迎候到指引道别
5. **电话接听礼仪** —— 三声接起、报部门、复述确认、转接、后挂机
6. **退房结账与送客** —— 收卡、查房核账、退押金、征询意见
7. **宾客投诉处理** —— 倾听、共情、致歉、行动、回访

讲稿依据酒店业通用的前厅部服务规范整理编写，为原创文本，未逐字引用任何单一
培训教材或视频。

## 文件说明

| 文件 | 作用 |
|---|---|
| `script_content.py` | 讲稿与分镜数据（章节、要点板条目、逐句旁白与要点亮起时机） |
| `art_lobby.py` | 大堂场景绘制，分房间层 / 前台层 / 光照三部分，便于把角色夹在台后 |
| `art_person.py` | 前台接待员角色绘制，4 种口型 × 3 种眼睛状态共 12 个变体 |
| `compose.py` | 版式合成：片头卡、章节卡、主版式（角色 + 要点板 + 字幕） |
| `tts_engine.py` | 可插拔的中文配音引擎（MeloTTS / Kokoro / Matcha / Piper） |
| `build.py` | 主流程：语音合成 → 时间轴 → 逐帧渲染 → ffmpeg 编码 |
| `download_voices.sh` | 下载 TTS 模型（全部取自 GitHub Release） |

## 实现要点

**画面**：全部用 PIL 图元绘制，2～3 倍超采样后缩放抗锯齿。场景拆成三层，
角色合成在房间层与前台层之间，形成"站在前台后面"的纵深。

**逐帧渲染的加速**：12 个表情变体各预合成一张完整场景，它们彼此只在头部
一小块矩形（`compose.HEAD_BOX`）内不同。渲染时每帧只搬运这一小块，
1080p 全片 12598 帧约 3 分钟完成。

**口型同步**：按帧长切分该句音频，计算 RMS 包络并归一化，映射到 4 档口型；
眨眼按 2.6～5.4 秒随机间隔插入。

**旁白**：默认使用 MeloTTS 中文模型（44.1kHz），逐句合成后按时间轴拼接，
句间停顿 0.34 秒、章节首尾 0.6 / 0.95 秒，最后由 ffmpeg 做 EBU R128 响度归一。
逐句结果会缓存在 `build/audio/<引擎名>/`，改动个别句子时只重合成那一句。

### 配音引擎选型

主流中文 TTS（GPT-SoVITS、CosyVoice、F5-TTS、IndexTTS、FishSpeech 等）权重普遍
只托管在 HuggingFace 或 ModelScope。若部署环境只放行 github.com，这些都取不到。

`k2-fsa/sherpa-onnx` 把多个模型转成 ONNX 并**直接挂在 GitHub Release** 上，
因此成为这里的可行解。四个可选引擎：

| `--tts` | 模型 | 采样率 | 合成实时率 | 说明 |
|---|---|---|---|---|
| `melo` | MeloTTS 中文 | 44100 Hz | ~1.0x | **默认**，音质最好 |
| `kokoro` | Kokoro 多语种 | 24000 Hz | ~1.3x | 支持中英混读 |
| `matcha` | Matcha 标贝中文 | 22050 Hz | ~3.3x | 最快，适合快速预览 |
| `piper` | Piper 中文 | 16000 Hz | ~8x | 体积最小的兜底方案 |

`--speed` 控制语速，小于 1 更慢；培训讲解默认 0.90。

## 重新生成

```bash
pip install pillow numpy sherpa-onnx piper-tts
# 需要 ffmpeg 与 Noto Sans CJK 字体
apt-get install -y ffmpeg fonts-noto-cjk

# 下载中文语音模型（约 600MB，全部来自 GitHub Release）
bash download_voices.sh voices
export TTS_MODEL_DIR=$PWD/voices

python3 build.py                                     # 完整成片
python3 build.py --tts kokoro                        # 换一个配音引擎
python3 build.py --tts matcha --limit 6 --out output/_test.mp4   # 快速预览前 6 句
```

`assets/` 下的图层与角色变体会被缓存复用；改动绘制代码后删除对应 PNG 即可重绘。
