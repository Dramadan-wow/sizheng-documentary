"""水墨素材:宣纸、远山、深墨底、雾、飞白笔触(黑/红)、朱砂日。全部程序生成,不用外部图片。用法:python gen_ink.py <输出目录>(约 1 分钟)"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageFilter
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("output", nargs="?", default="ink", help="水墨纹理输出目录")
OUT = ap.parse_args().output
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def noise(h, w, scale, octaves=5, sx=1.0, seed=None):
    """分形值噪声,0..1。sx>1 时横向拉长(纤维、笔触丝)。"""
    r = np.random.default_rng(seed) if seed is not None else rng
    acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        gh = max(2, int(h / scale * 2 ** o)); gw = max(2, int(w / (scale * sx) * 2 ** o))
        g = r.random((gh, gw)).astype(np.float32)
        acc += amp * np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
        tot += amp; amp *= .5
    a = acc / tot
    return (a - a.min()) / (a.max() - a.min() + 1e-6)


def save_rgba(rgb, alpha, name):
    a = np.clip(alpha, 0, 1)
    img = np.dstack([np.broadcast_to(np.array(rgb, np.float32), alpha.shape + (3,)), a * 255]).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, name))


H, W = 1080, 1920
# 宣纸:暖白底,大片晕染 + 纤维 + 细点 + 暗角
blot = noise(H, W, 260, 4); fib = noise(H, W, 9, 3, sx=2.5); fine = noise(H, W, 2, 2); speck = rng.random((H, W)) > .9993
yy, xx = np.mgrid[0:H, 0:W]; vig = ((xx - W / 2) / (W / 1.6)) ** 2 + ((yy - H / 2) / (H / 1.4)) ** 2
base = np.array([239, 233, 220], np.float32)
img = base[None, None, :] * (1 - .05 * (blot[..., None] - .5) * 2) * (1 - .012 * (fib[..., None] - .5) * 2) * (1 - .015 * (fine[..., None] - .5) * 2) * (1 - .10 * np.clip(vig, 0, 1)[..., None])
img[speck] *= .82
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "paper.jpg"), quality=93)

# 深墨底:近黑,淡淡的水渍
wash = noise(H, W, 340, 5); grain = noise(H, W, 3, 2)
d = np.array([20, 19, 18], np.float32)[None, None, :] + (wash[..., None] ** 2) * np.array([26, 24, 22], np.float32) + (grain[..., None] - .5) * 6
d *= (1 - .35 * np.clip(vig, 0, 1)[..., None])
Image.fromarray(np.clip(d, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "ink_dark.jpg"), quality=93)


def ridge(w, base, amp, scale, seed):
    r = np.random.default_rng(seed); y = np.zeros(w)
    for o in range(6):
        n = max(2, int(w / scale * 2 ** o)); g = r.random(n)
        y += amp / 2 ** o * np.interp(np.linspace(0, n - 1, w), np.arange(n), g)
    return base - y


def mountains(h, w, layers, name, color=(26, 24, 22)):
    """远山淡、近山浓;山脊处墨重,往下化成雾。"""
    A = np.zeros((h, w), np.float32); Y = np.arange(h)[:, None]
    for (base, amp, scale, alpha, fade, blur, seed) in layers:
        top = ridge(w, base, amp, scale, seed)[None, :]
        below = Y - top
        a = np.where(below > 0, alpha * np.exp(-below / fade), 0)
        a += np.where((below > 0) & (below < 10), alpha * .45 * (1 - below / 10), 0)          # 山脊墨线
        tex = noise(h, w, 70, 4, sx=.8, seed=seed + 100)
        a *= .78 + .44 * tex                                                                   # 皴擦
        a = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255
        A = 1 - (1 - A) * (1 - a)
    save_rgba(color, A, name)


mountains(720, W, [(420, 200, 520, .16, 140, 6, 1), (470, 200, 380, .26, 110, 3.5, 2), (560, 170, 300, .42, 90, 2, 3), (690, 120, 240, .62, 70, 1.2, 4)], "mountains.png")
mountains(720, W, [(360, 230, 520, .10, 160, 7, 11), (470, 210, 380, .16, 120, 4, 12), (600, 170, 300, .24, 90, 2.5, 13)], "mountains_light.png", color=(214, 208, 198))

# 雾:横向的淡白雾带
m = noise(H, W, 300, 4, sx=3); m = np.clip((m - .45) * 2.2, 0, 1) ** 1.5 * .55
save_rgba((245, 242, 236), m, "mist.png")


def brush(w, h, color, name, seed, dry=.55):
    """飞白笔触:中间实、两端毛,越往后墨越干。"""
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32); u = X / w; v = (Y - h / 2) / (h / 2)
    edge = ridge(w, 0, 1, 60, seed); edge = (edge - edge.min()) / (np.ptp(edge) + 1e-6)
    half = (.62 + .32 * edge[None, :]) * np.clip(np.minimum(u / .05, 1), 0, 1) ** .5 * (1 - .25 * u)
    body = np.clip((half - np.abs(v)) / .08, 0, 1)
    streak = noise(h, w, 3, 3, sx=60, seed=seed + 1)
    dryness = np.clip((u - .35) / .6, 0, 1) * dry
    a = body * np.clip((streak - dryness * 1.25) * 3 + .45, 0, 1)
    a *= np.clip((1 - u) / .06, 0, 1)
    a *= .82 + .18 * noise(h, w, 30, 3, seed=seed + 2)
    save_rgba(color, a, name)


brush(1600, 240, (24, 22, 20), "brush_black.png", 21)
brush(1600, 240, (176, 32, 30), "brush_red.png", 22)
brush(1200, 180, (176, 32, 30), "brush_red_dry.png", 23, dry=.9)

# 朱砂日:边缘略毛的红圆,内部有晕
S = 900; Y, X = np.mgrid[0:S, 0:S].astype(np.float32); r = np.hypot(X - S / 2, Y - S / 2) / (S / 2)
ang = np.arctan2(Y - S / 2, X - S / 2); wob = .006 * np.sin(ang * 3 + 1) + .004 * np.sin(ang * 5 + 2) + .006 * (noise(S, S, 40, 3, seed=33) - .5)
edge = np.clip((.93 + wob - r) / .012, 0, 1)
inner = .86 + .14 * noise(S, S, 120, 4, seed=31)
save_rgba((190, 38, 30), edge * inner * .95, "sun.png")
print("ink textures done", os.listdir(OUT))
