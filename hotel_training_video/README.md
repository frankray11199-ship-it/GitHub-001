# 酒店前厅部服务礼仪培训视频

一套**全部由代码生成**的中文培训视频：程序化绘制酒店大堂与前台接待员角色，
离线合成中文旁白，逐帧渲染并编码为 1080p MP4。

## 成片

| | |
|---|---|
| 文件 | `output/酒店前厅部服务礼仪培训.mp4` |
| 时长 | 8 分 54 秒 |
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
| `download_voices.py` | 下载 TTS 模型（跨平台，全部取自 GitHub Release） |
| `platform_support.py` | 中文字体与 ffmpeg 的跨平台探测 |
| `run.py` | 一键入口：体检 → 装依赖 → 下模型 → 出片 |

## 实现要点

**画面**：全部用 PIL 图元绘制，2～3 倍超采样后缩放抗锯齿。场景拆成三层，
角色合成在房间层与前台层之间，形成"站在前台后面"的纵深。

**逐帧渲染的加速**：12 个表情变体各预合成一张完整场景，它们彼此只在头部
一小块矩形（`compose.HEAD_BOX`）内不同。渲染时每帧只搬运这一小块，
1080p 全片 13344 帧约 3 分钟完成。

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

## 在自己电脑上跑

只需要 **Python 3.9+**，其余依赖 `run.py` 会自动装。

```bash
git clone <本仓库>
cd hotel_training_video

python run.py --check     # 先体检：报告字体、ffmpeg、依赖是否就绪
python run.py --quick     # 只出前 8 句的预览片，几分钟内看到效果
python run.py             # 完整出片
```

首次运行会自动下载配音模型（melo 约 167MB，来自 GitHub Release），
存放在 `voices/`，之后复用。

**Windows** 用 `py run.py` 或 `python run.py`，命令完全一致。
`run.py` 会自动装 `imageio-ffmpeg`，所以**不必单独安装 ffmpeg**。
中文字体走系统自带的微软雅黑 / 苹方 / Noto，一般无需额外安装。

### 耗时参考

| 阶段 | 说明 |
|---|---|
| 下模型 | 首次约 1 分钟（167MB） |
| 语音合成 | melo 约 1x 实时，全片约 9 分钟；用 `--tts matcha` 约 3 分钟 |
| 逐帧渲染 + 编码 | 约 3 分钟（13344 帧） |

逐句语音缓存在 `build/audio/<引擎>/`，第二次跑只重渲染，几分钟就完事。

### 常用参数

```bash
python run.py --tts kokoro          # 换配音引擎: melo / kokoro / matcha / piper
python run.py --speed 0.85          # 语速，<1 更慢
python run.py --fps 30              # 帧率
python run.py --voices D:/models    # 模型放到别处
```

### 出问题时

| 现象 | 处理 |
|---|---|
| 找不到中文字体 | `python platform_support.py` 看探测结果；可设环境变量 `CJK_FONT` 指向任一中文字体文件 |
| 找不到 ffmpeg | `pip install imageio-ffmpeg`，或设环境变量 `FFMPEG` 指向可执行文件 |
| 模型下载慢或失败 | 单独重试 `python download_voices.py --engine melo`，已下好的会跳过 |
| 想直接调底层 | `python build.py --help`，`run.py` 只是它的一层封装 |

## 单独调用各环节

```bash
python download_voices.py --engine all      # 四个引擎的模型全下
python build.py --tts melo                  # 直接出片（需先设 TTS_MODEL_DIR）
python platform_support.py                  # 只看环境探测结果
python script_content.py                    # 统计讲稿字数与预估时长
```

`assets/` 下的图层与角色变体会被缓存复用；改动绘制代码后删除对应 PNG 即可重绘。
