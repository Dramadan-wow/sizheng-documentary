"""旁白:用 Qwen3-TTS 按文字描述“设计”一个声音,再以它为参照逐句生成全片,每句自动核对。

为什么分两步:VoiceDesign 每次调用都会重新“想象”音色,逐句生成时前后句像换了人(实测句间声纹相似度 0.4–0.6)。
先设计出一段满意的样音,再用 Base 模型以它为参照克隆,全片同一个声音(实测 0.72–0.93)。参照的是自己设计的合成声音,不涉及真人。

用法(在装了 qwen-tts 的环境里运行,见 references/tools.md):
  设计试音: python tts_voice.py design --model <VoiceDesign 目录> --out <目录> --text "一句旁白" --voice "名字=描述" [--voice ...]
  全片生成: python tts_voice.py clone  --model <Base 目录> --out <目录> --ref <选中的试音> --ref-text "试音念的原文" --lines lines.json [--seeds 1,2,3,4] [--only key_0,key_1]
    lines.json 形如 {"h_hook": ["第一句。", "第二句。"], ...};输出 <key>_<i>.wav 与 .json(text、dur),并打印每句的识别吻合度和声纹相似度。
    --seeds 给多个时,每句生成多遍,按“声纹接近参照 + 识别准确”挑最好的一版(慢,适合重做个别句)。
"""
import argparse, json, os, re, difflib, subprocess, time
from pathlib import Path
import numpy as np, soundfile as sf
from runtime import find_binary

YEAR = {str(y): "".join("零一二三四五六七八九"[int(c)] for c in str(y)) for y in range(1900, 2100)}


def spoken(s):
    """年份读成“一九七七年”而不是“一千九百七十七年”。"""
    return re.sub(r"(19\d\d|20\d\d)(?=年)", lambda m: YEAR[m.group(1)], s)


def load_model(path, device="cpu", dtype="auto", threads=None):
    import torch
    from qwen_tts import Qwen3TTSModel
    torch.set_num_threads(threads or os.cpu_count() or 1)
    if dtype == "auto":
        dtype = "float32" if device == "cpu" else "float16"
    return Qwen3TTSModel.from_pretrained(path, device_map=device, dtype=getattr(torch, dtype))


class Checker:
    """Whisper 核对念的字;ECAPA 声纹和参照比相似度。都只在 CPU 上跑。"""
    def __init__(self, ref_wav, whisper_model="large-v3-turbo", ecapa_model="speechbrain/spkrec-ecapa-voxceleb", cache_dir=None):
        import torch, librosa
        from faster_whisper import WhisperModel
        try:
            from speechbrain.inference.classifiers import EncoderClassifier
        except ImportError:
            from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy
        self.torch, self.librosa = torch, librosa
        cache_dir = cache_dir or os.path.join(os.path.dirname(ref_wav), "_check_cache")
        self.wm = WhisperModel(whisper_model, device="cpu", compute_type="int8", download_root=os.path.join(cache_dir, "whisper"))
        self.enc = EncoderClassifier.from_hparams(source=ecapa_model, savedir=os.path.join(cache_dir, "ecapa"),
                                                  run_opts={"device": "cpu"}, local_strategy=LocalStrategy.COPY)   # Windows 无权限建软链接,要 COPY
        x, sr = sf.read(ref_wav, dtype="float32")
        self.R, _ = self.emb(x, sr)

    def emb(self, x, sr):
        x = np.asarray(x, dtype=np.float32)
        if x.ndim == 2:
            x = x.mean(axis=1)
        if x.ndim != 1 or not len(x):
            raise ValueError("声纹输入必须是非空音频")
        y = self.librosa.resample(x, orig_sr=sr, target_sr=16000)
        with self.torch.no_grad(): e = self.enc.encode_batch(self.torch.tensor(y)[None]).squeeze().numpy()
        norm = np.linalg.norm(e)
        if not np.isfinite(norm) or norm <= 1e-12:
            raise ValueError("无法从该音频提取有效声纹，请更换参考音频")
        return e / norm, y

    def score(self, x, sr, text):
        e, y = self.emb(x, sr)
        hyp = "".join(s.text for s in self.wm.transcribe(y, language="zh", beam_size=5)[0])
        c = lambda s: re.sub(r"[^一-鿿0-9]", "", s)
        return float(e @ self.R), difflib.SequenceMatcher(None, c(spoken(text)), c(hyp)).ratio(), hyp


def design(a):
    voices = [v.split("=", 1) for v in a.voice]
    if any(len(v) != 2 or not v[0] or re.search(r'[\\/:*?"<>|]', v[0]) or v[0] in (".", "..") for v in voices):
        raise ValueError("--voice 必须为‘文件名=声音描述’，文件名不能包含路径分隔符")
    m = load_model(a.model, a.device, a.dtype, a.threads); os.makedirs(a.out, exist_ok=True)
    for name, ins in voices:
        t0 = time.time()
        wavs, sr = m.generate_voice_design(text=spoken(a.text), instruct=ins, language="Chinese")
        p = os.path.join(a.out, name + ".wav"); sf.write(p, wavs[0], sr)
        print(f"{name}: {len(wavs[0]) / sr:.1f}s 音频,用时 {time.time() - t0:.0f}s -> {p}", flush=True)


def clone(a):
    import torch
    FF = find_binary("ffmpeg", a.ffmpeg)
    lines = json.loads(Path(a.lines).read_text(encoding="utf-8-sig"))
    if not isinstance(lines, dict) or not all(isinstance(k, str) and re.fullmatch(r"[\w-]+", k) and isinstance(ss, list) and all(isinstance(s, str) and s.strip() for s in ss) for k, ss in lines.items()):
        raise ValueError("台词文件必须是 {段落标识: [非空句子, ...]}，标识只能含文字、数字、下划线和短横线")
    seeds = [int(s) for s in a.seeds.split(",")]
    m = load_model(a.model, a.device, a.dtype, a.threads); os.makedirs(a.out, exist_ok=True)
    ref = os.path.join(a.out, "_ref.wav")
    subprocess.run([FF, "-y", "-v", "error", "-i", a.ref, "-ac", "1", "-ar", "24000", ref], check=True)
    prompt = m.create_voice_clone_prompt(ref_audio=ref, ref_text=a.ref_text)
    ck = None if a.skip_check else Checker(ref, a.whisper_model, a.ecapa_model, a.cache_dir)
    only = set(a.only.split(",")) if a.only else None
    for k, ss in lines.items():
        for i, s in enumerate(ss):
            key = f"{k}_{i}"
            if only and key not in only: continue
            metadata = Path(a.out) / (key + ".json")
            if not only and metadata.exists() and (Path(a.out) / (key + ".wav")).exists():
                previous = json.loads(metadata.read_text(encoding="utf-8"))
                if previous.get("text") == s:
                    continue
            best = None
            for sd in seeds:
                torch.manual_seed(sd)
                wavs, sr = m.generate_voice_clone(text=spoken(s), language="Chinese", voice_clone_prompt=prompt)
                x = wavs[0].astype(np.float32)
                sim, acc, hyp = ck.score(x, sr, s) if ck else (None, None, "未自动核对")
                print(f"{key} 种子{sd} " + (f"声纹{sim:.2f} 字准{acc:.0%} {hyp}" if ck else hyp), flush=True)
                rank = sim + acc if ck else 0
                if best is None or rank > best[0]: best = (rank, x, sr, sim, acc)
                if not ck:
                    break
            _, x, sr, sim, acc = best
            sf.write(os.path.join(a.out, key + ".wav"), x, sr)
            metadata.write_text(json.dumps(dict(text=s, dur=round(len(x) / sr, 3), file=key + ".wav", sim=round(sim, 3) if ck else None, acc=round(acc, 3) if ck else None), ensure_ascii=False, indent=2), encoding="utf-8")
            flag = "" if ck and sim >= .7 and acc >= .85 else "   <-- 请人工试听核对"
            print(f"{key}: {len(x) / sr:.1f}s{flag}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("design"); d.add_argument("--model", required=True); d.add_argument("--out", required=True); d.add_argument("--text", required=True); d.add_argument("--voice", action="append", required=True)
    c = sub.add_parser("clone"); c.add_argument("--model", required=True); c.add_argument("--out", required=True); c.add_argument("--ref", required=True); c.add_argument("--ref-text", required=True)
    c.add_argument("--lines", required=True); c.add_argument("--seeds", default="7"); c.add_argument("--only")
    c.add_argument("--ffmpeg"); c.add_argument("--whisper-model", default="large-v3-turbo")
    c.add_argument("--ecapa-model", default="speechbrain/spkrec-ecapa-voxceleb")
    c.add_argument("--cache-dir"); c.add_argument("--skip-check", action="store_true", help="跳过自动核对，只生成第一个种子的音频；需人工试听")
    for parser in (d, c):
        parser.add_argument("--device", default="cpu", help="例如 cpu 或 cuda:0")
        parser.add_argument("--dtype", choices=("auto", "float32", "float16", "bfloat16"), default="auto")
        parser.add_argument("--threads", type=int)
    a = ap.parse_args()
    if a.threads is not None and a.threads < 1:
        ap.error("--threads 必须大于 0")
    try:
        (design if a.cmd == "design" else clone)(a)
    except (ValueError, OSError, ImportError) as exc:
        ap.exit(1, f"旁白处理失败：{exc}\n请检查 README 中的语音环境和模型配置。\n")
