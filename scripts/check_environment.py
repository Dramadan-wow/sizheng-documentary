"""Read-only checks; does not install packages or download models."""
import argparse
import importlib.util
import shutil
import subprocess
import sys
from runtime import find_binary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tts", action="store_true", help="同时检查可选语音依赖是否可发现")
    ap.add_argument("--ffmpeg")
    ap.add_argument("--ffprobe")
    args = ap.parse_args()
    failures = []
    ok = sys.version_info >= (3, 10)
    print(f"[{'OK' if ok else 'MISSING'}] Python {sys.version.split()[0]}（要求 3.10+，推荐 3.12）")
    if not ok:
        failures.append("Python")
    modules = ["numpy", "PIL", "soundfile"]
    if args.tts:
        modules += ["qwen_tts", "torch", "torchaudio", "faster_whisper", "speechbrain", "librosa"]
    for module in modules:
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            available = False
        print(f"[{'OK' if available else 'MISSING'}] Python module: {module}")
        if not available:
            failures.append(module)
    for name in ("ffmpeg", "ffprobe"):
        try:
            binary = find_binary(name, getattr(args, name))
            result = subprocess.run([binary, "-version"], capture_output=True, text=True, timeout=15)
            if result.returncode:
                raise RuntimeError(f"退出码 {result.returncode}")
            print(f"[OK] {name}: {binary}")
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            print(f"[MISSING] {name}: {exc}")
            failures.append(name)
    node = shutil.which("node")
    try:
        version = subprocess.check_output([node, "--version"], text=True, timeout=15).strip() if node else ""
        parts = tuple(int(p) for p in version.lstrip("v").split(".")[:2])
        node_ok = parts >= (22, 2)
    except (OSError, ValueError, subprocess.SubprocessError):
        node_ok, version = False, "未发现或无法运行"
    print(f"[{'OK' if node_ok else 'MISSING'}] Node.js {version}（OpenFilm 要求 22.2+）")
    if not node_ok:
        failures.append("node")
    openfilm = shutil.which("openfilm")
    print(f"[{'OK' if openfilm else 'MISSING'}] OpenFilm: {openfilm or '请运行 npm install --global openfilm'}")
    if not openfilm:
        failures.append("openfilm")
    print("仅检查依赖可发现性及基础命令，不证明模型、二进制兼容性或完整渲染成功。")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
