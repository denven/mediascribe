# MediaScribe 快速开始

Language: [English](quickstart.md) | **Chinese**

这份指南帮助你在大约 5 分钟内，从零跑通一次转写或总结流程。

## 1. 安装

```bash
uv venv --python 3.11
```

按场景安装依赖：

```bash
# Cloud ASR + summary
uv sync

# Remote video support
uv sync --extra video

# Local ASR support
uv sync --extra local

# Local ASR + remote video
uv sync --extra local --extra video
```

如果要使用本地总结模型，先安装 Ollama，确认服务正在运行，再拉取默认模型：

```bash
ollama pull qwen2.5:3b
# 如果 Ollama 没有在后台运行：
ollama serve
```

## 2. 最小 `.env`

```env
HF_TOKEN=hf_xxx
MEDIASCRIBE_LLM_MODEL=ollama/qwen2.5:3b
# 仅用于本地 / `ollama/...` 总结模型。
MEDIASCRIBE_LLM_API_BASE=http://localhost:11434
AZURE_SPEECH_KEY=xxx
AZURE_SPEECH_REGION=westus2
```

说明：
- `HF_TOKEN` 主要用于本地 ASR
- MediaScribe 默认使用本地 Ollama 总结模型 `ollama/qwen2.5:3b`
- 如果你只想输出 transcript，可加 `--no-summary`
- 如果想改用云端模型，可传 `--llm-model`，并在 `.env` 中填写对应 API key
- `MEDIASCRIBE_LLM_API_BASE` 适合 Ollama 这类本地 / 自定义端点，不适合 `gpt-5-mini` 这样的云端模型

## 3. 推荐命令

- `mediascribe`
- `mediascribe-transcriber`
- `mediascribe-text`

## 4. 建议先尝试的命令

### 音频 -> 转写 + 总结

```bash
uv run mediascribe ".\meeting.wav" --asr azure
```

Azure 提示：如果你设置 `-l/--language`，请使用 `zh-CN`、`en-US` 这样的完整 locale。

### 音频 -> 仅转写

```bash
uv run mediascribe ".\meeting.wav" --asr azure --no-summary
```

### 已有 transcript -> 只做总结

```bash
uv run mediascribe .\output --summary-only
```

### 文本目录

```bash
uv run mediascribe-text .\notes
```

### 显式指定本地总结模型

```bash
uv run mediascribe-text .\notes --llm-model ollama/qwen2.5:3b --llm-api-base http://localhost:11434
```

### 视频总结

```bash
uv run mediascribe video ".\lesson.mp4" --asr azure
```

## 5. 本地硬件提示

### 本地 ASR

- `--asr local` 会明显增加本地 CPU、GPU 和内存占用
- `Whisper small` 更适合低配机器先跑通
- `Whisper medium` 是当前默认值，但通常需要更强一些的机器

### 本地总结

- 默认本地总结模型：`ollama/qwen2.5:3b`
- 实用起步参考：CPU-only 约 `6-8 GB RAM`，或 `4-6 GB VRAM`
- 如果机器更弱，可先试 `ollama/llama3.2:1b`

### 云端 ASR / 云端总结

- 可以显著降低本地硬件占用
- 可能产生服务费用

## 6. 视频说明

默认视频策略：
1. 优先尝试字幕
2. 没有可用字幕时提取或下载音频
3. 需要时执行 ASR
4. 生成总结

仅提取音频：

```bash
uv run mediascribe video ".\lesson.mp4" --extract-audio-only -o .\output
```

之后再把提取出的音频当作普通音频处理：

```bash
uv run mediascribe ".\output\media\lesson.wav" --asr azure
```

视频 ASR 路径也支持说话人命名：

```bash
uv run mediascribe video ".\lesson.mp4" --force-asr --asr azure --speaker-name Alice --speaker-name Bob
```

## 7. 远程视频认证

```env
YTDLP_COOKIES_FILE=.\cookies\global.txt
YTDLP_COOKIES_FROM_BROWSER=chrome:Profile 12
YTDLP_SITE_COOKIE_MAP=bilibili.com=.\cookies\bilibili_profile12.txt
```

查看认证决策：

```bash
uv run mediascribe doctor-video-auth "https://www.bilibili.com/video/BV1VtcYzTEZn/"
```

## 8. Verbose 日志

- `-v` 会显示 MediaScribe 自己的调试日志，不会默认刷出底层第三方 HTTP 调试细节
- 如果你需要同时查看 `openai` / `httpcore` / `LiteLLM` 的底层日志，可设置 `MEDIASCRIBE_DEBUG_THIRD_PARTY=1`

## 9. License

MediaScribe 使用 MIT License，详见 `../LICENSE`。

## 10. 继续阅读

- 主 README：`../README.md`
- 英文快速开始：`quickstart.md`
- 本地工作区：`local-workspace.zh-CN.md`
- 架构说明：`architecture.md`
- ASR 指南：`asr.md`
- Summary 指南：`summary.md`
- 性能记录：`benchmark-notes.md`
