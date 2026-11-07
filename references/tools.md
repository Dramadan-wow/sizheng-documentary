# 工具与环境

安装命令、环境变量和示例入口统一见 [README](../README.md)。本参考保留制作细节；不假设任何人的软件安装目录。

## 1. FFmpeg 与 SDR

`scripts/runtime.py` 按“命令参数 → `FFMPEG_BINARY` / `FFPROBE_BINARY` → PATH”查找工具。路径包含中文或空格可直接使用，脚本通过参数数组调用。

先用 ffprobe 确认色彩标记。只有确定输入为 BT.2020 HLG 时，才采用类似下面的转换滤镜；其他 HDR 标记需要另行选取：

```text
zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=120,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:param=0.35:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p
```

目标构建需包含相应滤镜，可用 `ffmpeg -filters` 检查。滤镜小数写成 `0.4` 等完整形式；不同 FFmpeg 版本的参数以本机帮助为准。

## 2. OpenFilm 时间线、字幕与渲染

- 官方安装：`npm install --global openfilm`。先确认 Node.js 22.2+ 和 FFmpeg 可用；运行 `openfilm render --help` 检查本机参数。
- 在工程目录调用 `openfilm open .`、`openfilm look 2`、`openfilm render --fps 30`。`look` 的图像存于 `.film/cache/look/`。
- `film.html` 的 `<section>` 是轨道，前面的轨道在上面；`<iframe>` 引用分镜页。`src="shots/title.html#t=0,4" at="0"` 表示使用该页的 0–4 秒并从全片第 0 秒开始。
- 分镜通过 `window.film={frame(t),ready}` 接口响应时间。`assets/kit.js` 提供了一组按时间求值的 DOM 动画。外部图片和字体在 ready 阶段加载。
- 当前协议把音视频转写放在同名 WebVTT 中，画面字幕通过时间线 caption track 添加。不要默认写旧的 `.film/subtitles.json` 或固定加 `--subtitles`；字幕样式与导出能力按安装版本验证。
- 分镜内的原生视频在新协议中可以被精确定位；原案例“不用分镜内 video”是旧版规避方案，不能当作通用限制。普通实拍优先放在时间线 `<video>` 中，更容易编辑。
- 局部导出可用 `openfilm render 420-480`，以本机帮助和实际输出位置为准。

### 旧版编码器补丁

`scripts/noenc.cjs` 会在当前 Node 进程中包装 `child_process.execFile`，仅过滤 `ffmpeg -encoders` 的硬件编码器列表。它不直接设置码率或 CRF，依赖 OpenFilm 当时的探测方式与回退实现。新版本优先用自身支持的编码设置；只有确认适用时才临时加载补丁：

```powershell
$previousNodeOptions = $env:NODE_OPTIONS
try {
  $patchPath = (Resolve-Path 'scripts/noenc.cjs').Path
  $env:NODE_OPTIONS = (($previousNodeOptions + ' --require="' + $patchPath + '"').Trim())
  # 在此窗口进入工程目录，再运行并检查一个短段的 openfilm render。
} finally {
  $env:NODE_OPTIONS = $previousNodeOptions
}
```

示例展示的是设置与恢复选项的范围；实际渲染命令应放在 try 块内。不要永久改变其他 Node 程序的环境。无法证实编码器和效果时不宣称补丁已生效。

### 最终导出

`scripts/fill_black_export.py` 的默认目标为 30 fps，可用 `--fps` 修改。输入先统一帧率，再按帧冻结补短黑场；视频编码使用 x264 CRF 16。

- `--max-gap 0.5`：只补不超过该秒数的中间黑场。前一帧不存在的开头黑场保留。
- `--keep-end 1.0`：保留片尾末尾范围内的淡出。
- `--tail` 与 `--split` 必须一起提供。尺寸应一致，分割点按帧对齐；因为重新编码，不要求关键帧。
- 默认不覆盖输出；`--overwrite` 显式允许覆盖输出文件，但输出必须不同于输入。
- 无音轨输入补静音；输出检查剩余黑场、解码与响度。静音会得到极低的响度，不能据此断言声音正常。

## 3. 口播处理

原案例在大厅录音中取得过“先抬电平、再降噪”的较好结果。处理新素材时先听噪声和失真，再做短段比较；电平不足和远距离导致的吐字缺失是不同问题。

DeepFilterNet 是可选工具，安装方式见 [官方仓库](https://github.com/Rikorose/DeepFilterNet)，参数以安装版 `deep-filter --help` 为准。不要把 `24~30` 这样的经验范围直接当成一个数值传入命令。

降噪后可用 EQ、适量压缩和 loudnorm 统一响度。原案例的人声目标约 -16 LUFS、旁白约 -18 LUFS，只是试音起点；正式目标以平台、课程和混音听感为准。

## 4. 语音识别与声纹

faster-whisper large-v3-turbo 可用于口播核对和旁白筛查。需要时先抽成 16 kHz 单声道 PCM，再把数组传入识别器。字级时间戳配合能量曲线可以定位停顿，不能单凭一个阈值决定剪辑点。

SpeechBrain ECAPA 的相似度用于发现可能的音色漂移；阈值依赖语料，不能证明说话人身份。纯音乐、混响、静音可能误导模型，先确认确实存在可用人声。

Windows 使用 `LocalStrategy.COPY` 避免符号链接权限问题。本包修正了 `Checker` 的参考向量解包：`emb()` 的音频返回值不再进入向量乘法。自动核对仍需真人试听复核。

## 5. Qwen3-TTS

以 [Qwen 官方仓库](https://github.com/QwenLM/Qwen3-TTS)的 Python 接口为基础，独立环境安装 `requirements-tts.txt`。先用 VoiceDesign 做声音候选，再用 Base 以选中的合成声音为参照逐句生成。

- VoiceDesign 模型：`Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`。
- Base 模型：`Qwen/Qwen3-TTS-12Hz-0.6B-Base`。
- CPU 默认 float32；`--device`、`--dtype`、`--threads` 可以覆盖。不同硬件的速度差异很大，不保证原案例的生成耗时。
- `--model` 支持本地目录或模型 ID；模型 ID 首次运行会下载权重。
- `--cache-dir` 指定核对缓存，`--whisper-model` 和 `--ecapa-model` 指定核对模型。
- `--skip-check` 只生成、不评分，必须人工试听。不会据此声称“核对通过”。
- 年份的中文读法由 `spoken()` 处理。极短句音色漂移时，可试更完整的句子再裁切。
- 多种子候选数量由 `--seeds` 限定；不要无限重试。换声音或模型时使用新输出目录。

## 6. 下载

模型优先用上游说明的 Hugging Face / ModelScope 客户端取得完整目录，不要凭猜测漏掉 tokenizer 或配置。镜像由使用者自行配置，不在脚本里强制指定。

原包的 `scripts/download_parallel.py` 保留用于已确认支持 HTTP Range 的大文件服务器。它按长度检查，不提供内容哈希验证；不支持 Range 或返回异常分段的服务应改用官方客户端。

历史照片、音乐和外部影像根据来源上下文核实，记录实际使用的条目；下载规模与来源选择遵循当前项目要求。
