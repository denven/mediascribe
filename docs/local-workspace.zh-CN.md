# 本地工作区

Language: [English](local-workspace.md) | **Chinese**

这份说明用于约定一套简单的本地工作目录结构，方便日常使用 MediaScribe 时区分源码、文档、输入素材和本地认证文件。

## 推荐目录

### `audios/`

可作为本地素材投放目录，用来放：
- 会议录音
- 访谈音频
- 手动测试用样例媒体
- 你希望和原始音频放在一起的笔记或总结

典型结构：

```text
audios/
  meeting-01.wav
  interview-a.m4a
  transcripts/
  summary.md
```

说明：
- 这里是本地工作目录，不是 Python 包源码目录
- 如果你希望一个目录自包含输入和输出，可以把生成的 `transcripts/` 和 `summary.md` 放在这里
- 如果你更喜欢输入输出分离，也可以把结果统一写到单独的 `output/` 目录

### `cookies/`

这个目录只建议用于本地 yt-dlp 认证文件，例如：
- 站点专用 cookies 导出文件
- 从浏览器导出的 cookies 文件
- 私有或受限视频源的临时认证文件

典型结构：

```text
cookies/
  global.txt
  bilibili.txt
```

说明：
- `cookies/` 下的内容都应视为敏感信息
- 不要提交真实 cookie 文件
- MediaScribe 的示例配置里会经常引用 `YTDLP_COOKIES_FILE` 和 `YTDLP_SITE_COOKIE_MAP`

## 生成目录

以下目录通常是运行时生成的临时或输出目录：
- `output/`
- `output_*`
- `transcripts/`
- `subtitles/`
- `media/`

它们已经在 `.gitignore` 中忽略，因此你可以放心保留本地运行结果，而不会污染仓库。

## 建议习惯

- 原始音频放在 `audios/`
- 认证材料放在 `cookies/`
- 面向用户的正式文档放在 `docs/`
- 内部规划、草稿、归档材料放在 `notes/`
- 非必要时，把生成输出都当作可丢弃内容
