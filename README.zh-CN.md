# MediaScribe

Language: [English](README.md) | **Chinese**

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![CLI](https://img.shields.io/badge/interface-CLI-2f7d32)
![ASR](https://img.shields.io/badge/ASR-local%20%7C%20cloud-0a7ea4)
![License](https://img.shields.io/badge/license-MIT-181717?style=flat-square&logo=github)

MediaScribe 是一个面向个人效率场景的实用 CLI，可对音频、文本、视频进行转写与总结，并支持一步完成或分步复用。

## 亮点
- 一个工具覆盖音频转写、transcript 总结、普通文本总结、视频总结
- 支持可复用的分步流程：先转写后总结，也支持一条命令直接跑完
- 同时支持本地与云端 ASR，且架构按 provider 解耦
- 视频链路支持字幕优先、ASR 回退、仅提取音频
- 输出会保留原始文件路径或远程 URL 等来源信息
- 转写与总结能力已抽象为可复用服务，便于被其他 Python 脚本直接调用

## 为什么是 MediaScribe

MediaScribe 的核心设计理念是“能力分层、组合复用”：
- 转写是独立服务
- 总结是独立服务
- 视频层只负责编排，优先走字幕，不行再走提音频 + ASR + 总结
- provider 适配层把本地实现与云端实现解耦，方便后续抽离复用

## 命令名称

推荐命令：
- `mediascribe`
- `mediascribe-transcriber`
- `mediascribe-text`

## 架构速览

```text
mediascribe
  -> transcription_service / audio_summary_service / text_summary_service / video_summary_service
    -> scanner / subtitle_fetch_service / media_extract_service / video_input_service
      -> asr providers (local / azure / aliyun / iflytek)
      -> summary providers (litellm-backed model routing)
      -> ffmpeg / yt-dlp
```

```text
Audio
  -> transcript
  -> optional summary

Text
  -> summary

Video
  -> subtitles first
  -> or extract/download audio
  -> transcript
  -> summary
```

## 安装

推荐使用 `uv`：

```bash
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

创建虚拟环境：

```bash
uv venv --python 3.11
```

如果要本地做文本总结，先安装 Ollama，并拉取默认模型：

```bash
ollama pull qwen2.5:3b
```

按场景安装依赖：

```bash
# Cloud ASR + summary
uv sync

# Add remote video support (yt-dlp)
uv sync --extra video

# Add local ASR
uv sync --extra local

# Local ASR + remote video
uv sync --extra local --extra video

# Development
uv sync --extra local --extra dev
```

## 最小 `.env` 配置

```env
# Local ASR (usually needed for local diarization)
HF_TOKEN=hf_xxx

# 本地总结模型（Ollama）
# 这两个值同时也是内置默认值。
MEDIASCRIBE_LLM_MODEL=ollama/qwen2.5:3b
MEDIASCRIBE_LLM_API_BASE=http://localhost:11434

# Azure ASR
AZURE_SPEECH_KEY=xxx
AZURE_SPEECH_REGION=westus2

# 可选云端总结 key
# ANTHROPIC_API_KEY=sk-xxx
# GEMINI_API_KEY=xxx
# DEEPSEEK_API_KEY=xxx
```

远程视频认证示例：

```env
YTDLP_COOKIES_FILE=.\cookies\global.txt
YTDLP_COOKIES_FROM_BROWSER=chrome:Profile 12
YTDLP_SITE_COOKIE_MAP=bilibili.com=.\cookies\bilibili_profile12.txt
```

更完整模板见 `.env.example`。

## 本地总结模型配置

MediaScribe 现在默认使用本地总结模型：
- 模型：`ollama/qwen2.5:3b`
- API 地址：`http://localhost:11434`
- 状态：已经通过当前 MediaScribe 总结链路完成实机联调验证

也可以通过 `.env` 或 CLI 覆盖：

```env
MEDIASCRIBE_LLM_MODEL=ollama/llama3.2:3b
MEDIASCRIBE_LLM_API_BASE=http://localhost:11434
```

```bash
uv run mediascribe-text .\notes --llm-model ollama/qwen2.5:3b --llm-api-base http://localhost:11434
```

如果你想改用云端模型，可以传 `--llm-model`，并在 `.env` 中提供对应的 API key。

手动联调验证命令：

```bash
uv run python scripts/manual_check_ollama_summary.py
```

## 快速开始

### 音频：转写 + 总结

```bash
uv run mediascribe ".\meeting.wav" --asr azure
```

### 音频：仅转写

```bash
uv run mediascribe ".\meeting.wav" --asr azure --no-summary
```

### 音频目录批量处理

```bash
uv run mediascribe .\audios --asr azure -o .\output
```

### 已有 transcript：只做总结

```bash
uv run mediascribe .\output --summary-only
```

### 文本或笔记目录

```bash
uv run mediascribe-text .\notes
```

### 显式指定本地总结模型

```bash
uv run mediascribe-text .\notes --llm-model ollama/qwen2.5:3b --llm-api-base http://localhost:11434
```

### 本地视频总结

```bash
uv run mediascribe video ".\lesson.mp4" --asr azure
```

### 远程视频总结

```bash
uv run mediascribe video "https://www.youtube.com/watch?v=aircAruvnKk"
```

## 典型工作流

### 音频一步完成

```bash
uv run mediascribe ".\meeting.wav" --asr azure
```

### 先转写，再总结

```bash
uv run mediascribe ".\meeting.wav" --asr azure --no-summary -o .\output
uv run mediascribe .\output --summary-only
```

### 在其他脚本中总结文本

```python
from pathlib import Path

from mediascribe.text_summary_service import summarize_raw_text_to_file

summary_path = summarize_raw_text_to_file(
    "Long text to summarize",
    output_dir=Path("manual_output"),
    source_name="manual-note",
    llm_model="ollama/qwen2.5:3b",
    llm_api_base="http://localhost:11434",
)

print(summary_path)
```

### 视频总结默认走字幕优先策略

```bash
uv run mediascribe video ".\lesson.mp4" --asr azure
```

默认视频策略：

1. 先尝试字幕
2. 没有可用字幕时提取或下载音频
3. 如有需要则执行 ASR
4. 生成总结

### 先提音频，后续再当音频处理

```bash
uv run mediascribe video ".\lesson.mp4" --extract-audio-only -o .\output
uv run mediascribe ".\output\media\lesson.wav" --asr azure
```

### 说话人命名

```bash
uv run mediascribe ".\meeting.wav" --speaker-name Alice --speaker-name Bob
```

视频走 ASR 路径时：

```bash
uv run mediascribe video ".\lesson.mp4" --force-asr --asr azure --speaker-name Alice --speaker-name Bob
```

## 硬件与成本说明

### Local ASR (`--asr local`)
- 会明显占用更多本地 CPU / GPU / 内存
- 适合希望尽量本地处理、并能接受更高硬件负载的场景
- 对于较长音视频或配置较弱的机器，云端 ASR 往往更实用

### Cloud ASR (`--asr azure` / `aliyun` / `iflytek`)
- 可显著降低本地硬件占用
- 通常更适合长音频或批量任务
- 可能产生云端 ASR 费用

### Summary generation
- 默认走本地 Ollama 模型：`ollama/qwen2.5:3b`
- 默认本地接口地址：`http://localhost:11434`
- 仍然支持通过 `--llm-model` + 对应 API key 使用云端模型
- 如果你只想拿 transcript，请加 `--no-summary`

## 视频说明与认证

### 支持的视频输入
本地视频文件
远程 URL，如 YouTube、Bilibili 以及其他 yt-dlp 支持的网站

### 视频认证尝试顺序

配置 cookies 后，MediaScribe 会按如下顺序尝试：

站点专用 cookies 文件
通用 cookies 文件
浏览器 profile cookies
无认证请求

可用以下命令查看认证决策：

```bash
uv run mediascribe doctor-video-auth "https://www.bilibili.com/video/BV1VtcYzTEZn/"
```

### Azure 长音频行为

对于 Azure 快速转写路径，MediaScribe 会在上传前自动切分高风险音频：
- 时长超过 60 分钟时自动切分
- 文件大于 150 MB 时自动切分
- 默认切片长度为 30 分钟

## 性能参考

以下数据来自当前机器和网络环境下的真实运行记录，属于端到端参考值，不代表严格保证。

| Scenario | Input Duration | Method | End-to-End Time | Approx Speed |
| --- | ---: | --- | ---: | ---: |
| Local MP4 `cleaned_...mp4` | 6m06s | local video -> extract audio -> Azure ASR -> 云端总结 | 1m41s | about 3.6x realtime |
| YouTube `3DlXq9nsQOE` | 18m30s | remote video -> download audio -> Azure ASR -> 云端总结 | 2m26s | about 7.6x realtime |
| YouTube `aircAruvnKk` with subtitles | 18m26s | remote subtitles -> 云端总结 | 31s | about 35.9x realtime |
| Facebook `1ahSKdqfDU` | 19s | remote video -> download audio -> Azure ASR -> 云端总结 | 36s | about 0.5x realtime |
| Bilibili `BV1VtcYzTEZn` | 2m59s | subtitle fail -> audio fallback -> Azure ASR -> 云端总结 | 58s to 1m04s | about 2.8x to 3.1x realtime |

更多说明：`docs/benchmark-notes.md`

## 项目结构

```text
mediascribe/
  cli.py
  transcription_service.py
  text_summary_service.py
  video_summary_service.py
  asr/
  summary/
  ffmpeg_utils.py
  yt_dlp_auth.py

docs/
examples/
```

说明：
- 项目名为 `MediaScribe`
- 规范的 Python 包路径现为 `mediascribe`

## 文档导航
- 快速上手: `docs/quickstart.zh-CN.md`
- 本地工作区: `docs/local-workspace.zh-CN.md`
- 架构说明: `docs/architecture.md`
- ASR API 与扩展指南: `docs/asr.md`
- Summary API 与扩展指南: `docs/summary.md`
- 第三方 provider 接入: `docs/plugin-providers.md`
- 性能参考记录: `docs/benchmark-notes.md`
- 自定义 provider 示例: `examples/custom_providers/README.md`

## License

本项目使用 MIT License，详见 `LICENSE`。

## 发布记录

见 `CHANGELOG.md`。

## 本地模型硬件参考

以下是更偏实战的起步参考，不是严格上限。真实占用会受音频长度、并发数、CPU/GPU 路径以及共享内存情况影响。

### 本地语音转写
| 模型 / 功能 | GPU 路径 | CPU 路径 | 说明 |
| --- | --- | --- | --- |
| `Whisper small` | 约 `2 GB VRAM` | 约 `8 GB RAM` | 适合先跑通流程 |
| `Whisper medium` | 约 `5 GB VRAM` | 约 `16 GB RAM` | 当前默认值，精度和速度比较平衡 |
| `Whisper turbo` | 约 `6 GB VRAM` | 约 `16 GB RAM` | 更快，但仍然偏吃资源 |
| `Whisper large` | 约 `10 GB VRAM` | 约 `16-32 GB RAM` | 效果更强，但本地负载最高 |
| `pyannote.audio` diarization 叠加 | 建议预留更多 GPU 空间 | 更适合 `16 GB RAM+` | 会明显抬高整套本地 ASR 的资源占用 |

### 本地文本总结
| 模型 | 下载体积 | CPU 路径 | GPU 路径 | 说明 |
| --- | --- | --- | --- | --- |
| `ollama/qwen2.5:3b` | 约 `1.9 GB` | `6-8 GB RAM` | `4-6 GB VRAM` | 最适合当前默认中文总结路线 |
| `ollama/llama3.2:1b` | 约 `1.3 GB` | `4-6 GB RAM` | `2-3 GB VRAM` | 最轻量 |
| `ollama/llama3.2:3b` | 约 `2.0 GB` | `6-8 GB RAM` | `4-6 GB VRAM` | 通用性更好 |
| `ollama/phi4-mini` | 约 `2.5 GB` | `8 GB RAM` | `4-6 GB VRAM` | 适合更强调结构化输出的场景 |

### 整机建议
| 硬件档位 | 建议组合 | 说明 |
| --- | --- | --- |
| `8 GB RAM` | `Whisper small` + `llama3.2:1b` | 或者直接使用云端 ASR，减轻本地压力 |
| `16 GB RAM` | `Whisper medium` + `qwen2.5:3b` | 最实用的平衡方案 |
| `32 GB RAM` 或 `8-12 GB VRAM` | 更强的 Whisper 变体 + 本地 diarization | 更适合长音频和连续本地运行 |
