"""补短黑场、可选拼接尾段、导出并检测；FFmpeg/ffprobe 可通过参数或环境变量配置。"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
from runtime import find_binary


def probe(path, ffprobe):
    result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    data = json.loads(result.stdout)
    if not any(s.get("codec_type") == "video" for s in data["streams"]):
        raise ValueError(f"没有视频流：{path}")
    return float(data["format"]["duration"]), any(s.get("codec_type") == "audio" for s in data["streams"])


def blacks(path, ffmpeg):
    result = subprocess.run([ffmpeg, "-v", "info", "-i", str(path), "-vf", "blackdetect=d=0.02:pix_th=0.12", "-an", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", result.stderr)]


def audio_filter(index, present, length, label):
    if present:
        return f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={length},asetpts=PTS-STARTPTS[{label}]"
    return f"anullsrc=r=48000:cl=stereo,atrim=duration={length},asetpts=PTS-STARTPTS[{label}]"


def export(args):
    ffmpeg, ffprobe = find_binary("ffmpeg", args.ffmpeg), find_binary("ffprobe", args.ffprobe)
    source, destination = Path(args.src).resolve(), Path(args.dst).resolve()
    if source == destination or (args.tail and Path(args.tail).resolve() == destination):
        raise ValueError("输出路径必须与输入不同")
    if destination.exists() and not args.overwrite:
        raise ValueError(f"输出已存在：{destination}；请换用新文件名，或显式使用 --overwrite")
    length, has_audio = probe(source, ffprobe)
    if args.tail and not (0 < args.split < length):
        raise ValueError("--split 必须在原片时长范围内，且大于 0")
    fps = args.fps
    intervals = blacks(source, ffmpeg)
    inputs = ["-i", str(source)]
    if args.tail:
        tail_length, tail_audio = probe(args.tail, ffprobe)
        total = args.split + tail_length
        intervals = [(s, min(e, args.split)) for s, e in intervals if s < args.split]
        intervals += [(s + args.split, e + args.split) for s, e in blacks(args.tail, ffmpeg)]
        inputs += ["-i", args.tail]
        head = (f"[0:v]trim=duration={args.split},fps={fps},setpts=PTS-STARTPTS[a];"
                f"[1:v]fps={fps},setpts=PTS-STARTPTS[b];"
                + audio_filter(0, has_audio, args.split, "aa") + ";"
                + audio_filter(1, tail_audio, tail_length, "ba") + ";"
                + "[a][aa][b][ba]concat=n=2:v=1:a=1[f0][au]")
    else:
        total = length
        head = f"[0:v]fps={fps},setpts=PTS-STARTPTS[f0];" + audio_filter(0, has_audio, total, "au")
    gaps = [(s, e) for s, e in intervals if round(s * fps) > 0 and e < total - args.keep_end and 0 < e - s <= args.max_gap]
    print(f"补 {len(gaps)} 处短黑场：" + ", ".join(f"{s:.3f}-{e:.3f}" for s, e in gaps), flush=True)
    chain = ""
    for i, (start, end) in enumerate(gaps):
        first = round(start * fps)
        last = max(first, round(end * fps) - 1)
        chain += f";[f{i}]split[p{i}][q{i}];[p{i}][q{i}]freezeframes=first={first}:last={last}:replace={first - 1}[f{i + 1}]"
    filters = head + chain + ";[au]alimiter=limit=0.84:level=false:attack=3:release=60[ao]"
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-y" if args.overwrite else "-n", "-v", "error", *inputs,
               "-filter_complex", filters, "-map", f"[f{len(gaps)}]", "-map", "[ao]",
               "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
               "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
               "-r", str(fps), "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
               "-movflags", "+faststart", str(destination)]
    subprocess.run(command, check=True)
    remaining = blacks(destination, ffmpeg)
    decoded = subprocess.run([ffmpeg, "-v", "error", "-i", str(destination), "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    loudness = subprocess.run([ffmpeg, "-nostats", "-i", str(destination), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stderr
    measured = re.findall(r"I:\s+(-?[\d.]+) LUFS", loudness)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", loudness)
    print(f"成片 {probe(destination, ffprobe)[0]:.2f}s | 剩余黑场 {remaining} | 响度 {measured[-1] if measured else '?'} LUFS | 峰值 {peak[-1] if peak else '?'} dBFS")
    if decoded.returncode or decoded.stderr.strip():
        raise RuntimeError("导出后解码检查失败：" + decoded.stderr[:500])
    print("解码检查通过；保留的长黑场、开头黑场和片尾淡出仍需人工确认。")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--tail"); ap.add_argument("--split", type=float)
    ap.add_argument("--fps", type=float, default=30, help="导出帧率，先统一帧率再按帧补黑，默认 30")
    ap.add_argument("--keep-end", type=float, default=1.0, help="保留片尾最后几秒内的淡出")
    ap.add_argument("--max-gap", type=float, default=0.5, help="只补不超过此秒数的短黑场")
    ap.add_argument("--ffmpeg"); ap.add_argument("--ffprobe")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if bool(args.tail) != (args.split is not None):
        ap.error("--tail 和 --split 必须一起提供")
    if not math.isfinite(args.fps) or args.fps <= 0 or not math.isfinite(args.keep_end) or args.keep_end < 0 or not math.isfinite(args.max_gap) or args.max_gap <= 0:
        ap.error("fps、max-gap 必须为正数，keep-end 必须大于等于 0")
    try:
        export(args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        ap.exit(1, f"导出失败：{exc}\n")


if __name__ == "__main__":
    main()
