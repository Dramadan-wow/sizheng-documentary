"""量配乐曲库每首曲子的响度曲线:有没有渐强、高潮在第几秒。挑“结尾高潮”用的曲子时先跑这个——
大多数免费配乐从头到尾一样响(实测 33 首里 20 首整首起伏不到 8 dB),撑不起高潮。

用法: python music_curves.py <曲库目录或若干音频文件>
输出每首:时长、峰值所在秒、动态范围、前三分之一到后段的抬升,以及每 10 秒一格的小曲线。
"""
import argparse, glob, os, subprocess, sys
import numpy as np
from runtime import find_binary

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("inputs", nargs="+", help="曲库目录或音频文件")
ap.add_argument("--ffmpeg")
args = ap.parse_args()
try:
    FF = find_binary("ffmpeg", args.ffmpeg)
except OSError as exc:
    ap.exit(1, f"{exc}\n")

files = []
for p in args.inputs:
    files += sorted(glob.glob(os.path.join(p, "*.mp3")) + glob.glob(os.path.join(p, "*.wav"))) if os.path.isdir(p) else [p]
rows = []
for p in files:
    r = subprocess.run([FF, "-v", "error", "-i", p, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, np.float32); sr = 8000; w = sr * 10
    if len(x) < w: continue
    seg = np.array([20 * np.log10(np.sqrt(np.mean(x[k:k + w] ** 2)) + 1e-9) for k in range(0, len(x) - w // 2, w)])
    third = max(1, len(seg) // 3); rise = seg[-third:].max() - seg[:third].mean(); dyn = seg.max() - np.percentile(seg, 10)
    bar = "".join("▁▂▃▄▅▆▇█"[int(np.clip((s - seg.max() + 24) / 24 * 7.99, 0, 7))] for s in seg)
    rows.append((rise, f"{os.path.basename(p)[:34]:34s} {len(x) / sr:5.0f}s 峰在{int(np.argmax(seg)) * 10:4d}s 动态{dyn:4.1f}dB 渐进{rise:+5.1f}dB  {bar}"))
for _, line in sorted(rows, reverse=True): print(line)
print("\n挑法:结尾那段选“渐进”和“动态”都大的;把曲子峰值对准片中最后一句情绪最高的台词,往前倒推入点。")
