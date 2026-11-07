"""大文件分段并行下载(HTTP Range),断了自动续传,最后按大小校验。
魔搭(ModelScope)单线程常只有 0.5 MB/s,8 段并行能到 5–13 MB/s;HF 镜像经 huggingface_hub 下载时常报 "Distant resource does not seem to be on huggingface.co"。

用法: python download_parallel.py <URL> <保存路径> <字节数> [段数=8]
字节数可从魔搭接口取: https://modelscope.cn/api/v1/models/<组织>/<模型>/repo/files?Recursive=true  (Files[].Size)
文件直链: https://modelscope.cn/models/<组织>/<模型>/resolve/master/<文件路径>
"""
import os, sys, threading, time, urllib.request

url, out, size = sys.argv[1], sys.argv[2], int(sys.argv[3]); parts = int(sys.argv[4]) if len(sys.argv) > 4 else 8
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)


def fetch(s, e, p):
    for _ in range(30):
        have = os.path.getsize(p) if os.path.exists(p) else 0
        if have >= e - s + 1: return
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={s + have}-{e}", "User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=60) as r, open(p, "ab") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
        except Exception:
            time.sleep(2)


step = size // parts; segs = []; ths = []
for i in range(parts):
    s = i * step; e = size - 1 if i == parts - 1 else (i + 1) * step - 1; p = f"{out}.part{i}"; segs.append((p, e - s + 1))
    t = threading.Thread(target=fetch, args=(s, e, p)); t.start(); ths.append(t)
t0 = time.time()
while any(t.is_alive() for t in ths):
    time.sleep(15); got = sum(os.path.getsize(p) for p, _ in segs if os.path.exists(p))
    print(f"{got / 1e6:.0f}/{size / 1e6:.0f} MB  {got / 1e6 / (time.time() - t0):.1f} MB/s", flush=True)
if not all(os.path.exists(p) and os.path.getsize(p) == n for p, n in segs): sys.exit("下载不完整,重跑会从断点续传")
with open(out, "wb") as f:
    for p, _ in segs:
        with open(p, "rb") as g:
            while (b := g.read(1 << 24)): f.write(b)
        os.remove(p)
print("完成", out, os.path.getsize(out) == size)
