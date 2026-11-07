# sizheng-documentary

用于思政课、校史人物及红色主题微纪录片的 Agent Skill，包含内容策划、补拍设计、声音处理、水墨分镜样式与 OpenFilm 制作参考。

**安装 skill 后可以复用制作方法；生成完整视频仍需要素材、本地工具和相应模型。** 本仓库不附带真人素材、音乐、字体或模型权重。

## 安装到 Claude Code

下载并解压，将整个 `sizheng-documentary` 文件夹放到以下任一位置，确保 `SKILL.md` 就在该文件夹第一层：

- 全局：`~/.claude/skills/sizheng-documentary/`。
- 当前项目：`<项目>/.claude/skills/sizheng-documentary/`。
- Windows 的 `~` 通常对应用户目录，例如 `%USERPROFILE%`，路径无需与原作者电脑一致。

已有同名 skill 时先备份，再更新其中的文件。启动 Claude Code 后输入 `/sizheng-documentary`，或描述要制作的纪录片。

示例请求：

> 使用 sizheng-documentary 帮我制作校史人物微纪录片。先检查我提供的素材和课程要求，给出脚本与补拍方案，再做水墨留白风格的短样片。学校、名单、时长和比例都按本项目提供的内容，不套用案例。

官方说明：[Claude Code Skills](https://code.claude.com/docs/en/skills)。其他支持 Agent Skills 的工具需按各自的安装位置和权限配置。

Claude 网页端可在 Customize → Skills 上传含 skill 文件夹的 ZIP。若手上是本项目导出的 `.skill` 文件，可复制一份改名为 `.zip` 再上传；该文件本身就是 ZIP 格式。上传不会把本地 Windows 工具或模型一并安装到云端，完整渲染需要另行适配。参见[官方上传说明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。

## 功能与依赖

| 要做什么 | 需要什么 |
| --- | --- |
| 写稿、分析结构、补拍方案 | 能读取 skill 的 AI 工具，以及本项目资料 |
| 生成静音示例工程 | Python 3.10+；推荐 3.12，仅使用标准库 |
| 水墨纹理、配乐响度分析 | `requirements.txt`；音频分析另需 FFmpeg |
| 预览、渲染 OpenFilm 工程 | Node.js 22.2+、OpenFilm、FFmpeg；首次运行会下载浏览器 |
| 本地合成旁白并自动核对 | 独立 Python 环境、`requirements-tts.txt`、语音模型；完整流程需数 GB 模型下载 |
| 可选口播降噪 | 单独安装 DeepFilterNet，不作为基础依赖强制安装 |

语音依赖文件固定 `qwen-tts==0.1.1`，并限制 PyTorch/Torchaudio 在 2.5–2.8 范围，避免旧语音库与新版音频 API 混装。它是兼容范围清单，不是覆盖所有平台的锁文件；安装后执行 `python -m pip check`。

## 最快体验：先生成 12 秒静音工程

在本仓库根目录运行，不需要语音模型、网络、字体下载或 API Key：

```sh
python scripts/create_project.py my-film --config examples/project.example.json
```

打开 `my-film/shots/title.html` 可以单独查看片头动画；完整时间线交给 OpenFilm。生成的工程包含片头、片尾和资料来源三页，是结构示例，不是满足课程时长要求的正式成片。

仓库已附 [examples/minimal-project/film.html](examples/minimal-project/film.html)，可先复制整个 `minimal-project` 文件夹再使用。

配置字段：

| 字段 | 用途 |
| --- | --- |
| `title` / `subtitle` / `team` / `seal` / `location` | 片名、副标题、组名、印章、地点，生成时写入分镜 |
| `credits` / `sources` | 片尾分工与实际来源 |
| `requirements` | 正式课程时长、实拍和引用比例；未知为 `null`，比例用 0–1 |
| `sample` | 这段演示中三页的时长，不替代正式成片时长 |
| `render.fps` | 制作简报中的目标帧率；调用渲染与导出时还需传入 `--fps` |
| `fonts` | 三种可选字体路径，`null` 时用系统回退；相对路径以配置文件所在目录为基准 |

`project.json` 是制作简报，修改后不会自动改写已有 HTML。可以直接编辑分镜，或用修改后的配置在新目录重建；生成器会拒绝覆盖非空工程。

## 安装基础环境

下面的 Python 安装命令从仓库根目录执行。

Windows PowerShell，无需激活脚本或更改执行策略：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

后续示例中的 `python` 请替换为所用虚拟环境的解释器路径，或自行激活环境。

FFmpeg 及 ffprobe 从 [FFmpeg 官方下载入口](https://ffmpeg.org/download.html) 安装。优先加入 PATH；也可用环境变量指定完整可执行文件路径，脚本不再依赖原作者的版本目录。

PowerShell（把路径改为自己的实际安装位置）：

```powershell
$env:FFMPEG_BINARY = 'D:\Tools\ffmpeg\bin\ffmpeg.exe'
$env:FFPROBE_BINARY = 'D:\Tools\ffmpeg\bin\ffprobe.exe'
```

macOS / Linux 示例：

```sh
export FFMPEG_BINARY=/opt/ffmpeg/bin/ffmpeg
export FFPROBE_BINARY=/opt/ffmpeg/bin/ffprobe
```

脚本参数 `--ffmpeg` / `--ffprobe` 优先于环境变量，环境变量优先于 PATH；变量值只填写路径，不附带命令参数。

安装并检查 OpenFilm：

```sh
npm install --global openfilm
openfilm render --help
python scripts/check_environment.py
```

如果只做内容策划或生成静音工程，可以暂不安装 OpenFilm 和 FFmpeg。环境检查会列出缺项并返回非零状态，不会自动安装或下载。它只检查模块能否发现，不证明 Torch 等二进制依赖能正常加载。

OpenFilm 的使用方式据 2026-11-08 核对的[官方 CLI](https://openfilm.dev/docs/cli/)与[协议文档](https://github.com/openfilm/openfilm/blob/main/packages/openfilm/SPEC.md)整理；不同版本先查帮助。原包的 `--subtitles`、旧字幕 JSON 和 `noenc.cjs` 不是新版必需配置。

进入刚创建的工程目录后：

```sh
openfilm open .
openfilm look 2
openfilm render --fps 30
```

`film.html` 描述完整时间线，`shots/*.html` 是分镜，`shots/ink.css` 和 `shots/kit.js` 是可随工程复制的样式与动画。渲染命令中的 30 应与配置的目标帧率一致。

## 字体与水墨素材

默认示例使用系统衬线字体，所有页面无需请求外部字体或图片。需要原风格时自行下载 [Noto Serif SC](https://fonts.google.com/noto/specimen/Noto+Serif+SC) 与 [Zhi Mang Xing](https://fonts.google.com/specimen/Zhi+Mang+Xing)，保留各自随附的授权文件。

在配置的 `fonts.serif_regular`、`fonts.serif_bold`、`fonts.brush` 填入对应的本地字体路径，再生成新工程；同一可变宋体文件也可以同时用于两个宋体字段。生成器会复制文件并生成 `shots/fonts.css`。

生成水墨纹理：

```sh
python scripts/gen_ink.py my-film/assets/ink
```

然后在需要的分镜中加入 `<div class="coal"></div>`，替换示例的 `.paper` 背景。生成脚本使用固定随机种子，资源可重复生成；具体版式见 [风格参考](references/style_liubai.md)。

## 可选：本地合成旁白

完整语音环境建议用独立 Python 3.12 环境。Windows：

```powershell
python -m venv .venv-tts
.\.venv-tts\Scripts\python.exe -m pip install -r requirements-tts.txt
.\.venv-tts\Scripts\python.exe -m pip check
.\.venv-tts\Scripts\python.exe scripts/check_environment.py --tts
```

macOS / Linux 使用 `.venv-tts/bin/python` 执行相同的 pip 和脚本参数。

CPU 可运行但较慢，实际时间和内存占用取决于硬件。GPU 用户应按 [PyTorch 官方安装说明](https://pytorch.org/get-started/locally/)选择配套的 Torch/Torchaudio 构建。Windows 若遇到库加载错误，检查配套版本和音频工具，不要直接修改全局 Python 环境。

脚本的 `--model` 接受本地模型目录或 Hugging Face 模型 ID；传模型 ID 会在首次运行时下载权重。模型下载方法见 [Qwen 官方仓库](https://github.com/QwenLM/Qwen3-TTS)。模型和缓存不要提交到本仓库。

先设计一段合成参考声音：

```sh
python scripts/tts_voice.py design --model Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign --out generated/voices --text "每一段校园记忆，都从一个真实的问题开始。" --voice "warm=中年男性，嗓音低沉温暖，语速舒缓，吐字清晰，庄重克制的人文纪录片旁白"
```

试听后选择参考声音，逐句生成：

```sh
python scripts/tts_voice.py clone --model Qwen/Qwen3-TTS-12Hz-0.6B-Base --out generated/narration --ref generated/voices/warm.wav --ref-text "每一段校园记忆，都从一个真实的问题开始。" --lines examples/lines.example.json --cache-dir generated/check-cache
```

`--ref-text` 必须与所选参考音频实际念出的文字一致。自动核对会另外加载 Whisper 与 ECAPA 模型；`--whisper-model`、`--ecapa-model` 可指定自己的模型位置。需要先试听合成结果时可加 `--skip-check`，此时仅生成第一个种子的结果，JSON 的 `sim`、`acc` 为 `null`，不能声称自动核对通过。使用 GPU 时可指定 `--device cuda:0`；CPU 默认 float32。

默认不强制使用第三方模型镜像。需要时在自己的环境设置 `HF_ENDPOINT` / `HF_HOME`。换参考声音或模型时使用新的输出目录；未指定 `--only` 时，已有音频和相同台词的元数据会被视为可续用。

自动识别与声纹分数不能替代人工试听，也不会自动把音频、音乐和字幕组装成整片。

## 导出与补黑场

```sh
python scripts/fill_black_export.py my-film/render.mp4 generated/final-v1.mp4 --fps 30
```

`render.mp4` 是示意文件名，请替换为 OpenFilm 实际导出的文件。脚本默认保留已有输出，不覆盖原片；可用 `--overwrite` 显式覆盖另一个已存在的输出文件。

默认只补不超过 0.5 秒的中间黑场，保留开头黑场与片尾最后 1 秒内的淡出。若作品有有意设计的短黑场，应先检查或调整参数。无音轨输入会添加静音轨，以便统一导出。

重渲片尾后拼接：

```sh
python scripts/fill_black_export.py generated/previous.mp4 generated/final-v2.mp4 --tail generated/tail.mp4 --split 420 --fps 30
```

`--split` 是原片上尾段替换起点；尾段自己的时间从 0 开始。两段的视频尺寸应一致，分割点按目标帧率对齐。本脚本会重新编码，不要求 copy 拼接的关键帧条件，也会检查尾段内的短黑场。

配乐起伏分析：

```sh
python scripts/music_curves.py path/to/music
```

## 验证与发布

运行基础回归检查（不下载语音模型）：

```sh
python -m unittest discover -s tests -v
```

测试覆盖工程生成、HTML 文本转义、字体路径、拒绝覆盖、声纹返回值、FFmpeg 路径发现，以及在可用时的真实补黑场与尾段拼接。FFmpeg 未安装时，相应视频集成测试会显示跳过。

把当前目录内容作为 GitHub 仓库源码上传，保留 `SKILL.md`、`scripts/`、`references/`、`assets/` 和 `examples/` 的相对位置。发布安装 ZIP 时，压缩包最外层应为单个 `sizheng-documentary/` 文件夹，`SKILL.md` 在该文件夹内。`.skill` 可使用相同 ZIP 内容。

验证范围与本机限制见 [VALIDATION.md](VALIDATION.md)。本次整理不代替作者选择开源许可证；仓库公开发布时应明确希望给予使用者的授权。
