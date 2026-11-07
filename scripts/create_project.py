"""Create a self-contained, silent OpenFilm sample without model downloads."""
import argparse
import copy
import html
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def validate_config(config):
    for key in ("title", "subtitle", "team", "seal", "location"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"{key} 必须是非空字符串")
    if not isinstance(config.get("credits"), dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in config["credits"].items()
    ):
        raise ValueError("credits 必须是‘分工: 姓名’的字符串对象")
    if not isinstance(config.get("sources"), list) or not all(isinstance(s, str) for s in config["sources"]):
        raise ValueError("sources 必须是字符串列表")
    for key in ("title_seconds", "credits_seconds", "sources_seconds"):
        value = config.get("sample", {}).get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"sample.{key} 必须是正数")
    fps = config.get("render", {}).get("fps")
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0:
        raise ValueError("render.fps 必须是正数")
    requirements = config.get("requirements", {})
    for key in ("min_live_action_ratio", "max_external_ratio"):
        value = requirements.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1):
            raise ValueError(f"requirements.{key} 必须为 null 或 0 到 1 的数字")
    for key in ("duration_seconds_min", "duration_seconds_max"):
        value = requirements.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
            raise ValueError(f"requirements.{key} 必须为 null 或正数")
    minimum, maximum = (requirements.get(k) for k in ("duration_seconds_min", "duration_seconds_max"))
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("最短时长不能大于最长时长")


def page(title, body, duration):
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=1920, height=1080">
<title>{html.escape(title)}</title><link rel="stylesheet" href="ink.css"><link rel="stylesheet" href="fonts.css">
<style>
body {{ background:#efe9dc; }}
.paper {{ position:absolute; inset:0; background:radial-gradient(ellipse at 18% 30%,#f8f3e8,transparent 65%),linear-gradient(155deg,#ece4d4,#f4eee2 55%,#e4dac7); }}
.paper::after {{ content:""; position:absolute; left:0; right:0; bottom:0; height:280px; background:linear-gradient(170deg,transparent 45%,#746f6230 46%,#dad4c4 75%); }}
.content {{ position:absolute; inset:150px 180px; display:flex; flex-direction:column; justify-content:center; gap:38px; }}
h1 {{ font-size:112px; line-height:1.25; max-width:1500px; overflow-wrap:anywhere; }}
p {{ font-size:40px; line-height:1.65; }}
.sources {{ font-size:34px; }}
.line {{ height:4px; width:180px; background:#b3221f; }}
.seal {{ right:160px; top:140px; width:100px; height:100px; font-size:32px; }}
</style></head><body class="pp" data-len="{duration:g}"><div class="paper"></div>
{body}
<script src="kit.js"></script><script>
window.film.duration={duration:g}; window.film.width=1920; window.film.height=1080;
if (!window.filmHost) {{
  const ready=window.film.ready;
  Promise.resolve(typeof ready==='function'?ready():ready).then(() => {{
    const start=performance.now();
    function tick(now) {{ window.film.frame(((now-start)/1000)%window.film.duration); requestAnimationFrame(tick); }}
    requestAnimationFrame(tick);
  }});
}}
</script></body></html>
'''


def create_project(output, config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    validate_config(config)
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"输出目录不是空目录：{output}；请使用新目录以保留已有剪辑")
    fonts = []
    for key, filename, family, weight in (
        ("serif_regular", "SerifSC-600.ttf", "Serif", 600),
        ("serif_bold", "SerifSC-900.ttf", "Serif", 900),
        ("brush", "ZhiMangXing.ttf", "Brush", 400),
    ):
        value = config.get("fonts", {}).get(key)
        if value:
            source = Path(value).expanduser()
            if not source.is_absolute():
                source = config_path.parent / source
            if not source.is_file():
                raise ValueError(f"字体文件不存在：{source}")
            fonts.append((key, source, filename, family, weight))
    shots = output / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    (output / "assets").mkdir(exist_ok=True)
    for asset in ("ink.css", "kit.js"):
        shutil.copy2(ROOT / "assets" / asset, shots / asset)
    fonts_css = []
    local_config = copy.deepcopy(config)
    for key, source, filename, family, weight in fonts:
        target = output / "assets" / "fonts" / filename
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
        local_config["fonts"][key] = "assets/fonts/" + filename
        fonts_css.append(f"@font-face {{ font-family:{family}; src:url('../assets/fonts/{filename}'); font-weight:{weight}; }}")
    (shots / "fonts.css").write_text("\n".join(fonts_css) + "\n", encoding="utf-8")
    escape = html.escape
    seal = "<br>".join(escape(ch) for ch in config["seal"])
    title_body = f'''<div class="content" data-in="0" data-fade="0.6"><p class="red serif">{escape(config['subtitle'])}</p>
<h1 class="brush">{escape(config['title'])}</h1><div class="line"></div>
<p class="grey serif">{escape(config['team'])} · {escape(config['location'])}</p></div>
<div class="seal" data-pop="0,0.7,1.15">{seal}</div>'''
    credit_lines = "".join(f"<p>{escape(role)}：{escape(name)}</p>" for role, name in config["credits"].items())
    credits_body = f'<div class="credits" data-in="0" data-fade="0.6"><h1 class="brush">谢谢观看</h1><p>{escape(config["team"])}</p>{credit_lines}</div>'
    source_lines = "".join(f'<p class="sources">{escape(line)}</p>' for line in config["sources"])
    sources_body = f'<div class="content" data-in="0" data-fade="0.6"><h1 class="brush red">资料来源</h1><div class="line"></div>{source_lines}</div>'
    clips, at = [], 0.0
    for name, body, duration in (
        ("title", title_body, config["sample"]["title_seconds"]),
        ("credits", credits_body, config["sample"]["credits_seconds"]),
        ("sources", sources_body, config["sample"]["sources_seconds"]),
    ):
        (shots / f"{name}.html").write_text(page(config["title"], body, duration), encoding="utf-8")
        clips.append(f'<iframe id="{name}" src="shots/{name}.html#t=0,{duration:g}" at="{at:g}"></iframe>')
        at += duration
    film = '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1920, height=1080"><title>' + escape(config["title"]) + '</title></head><body>\n<section>\n' + "\n".join(clips) + '\n</section>\n</body></html>\n'
    (output / "film.html").write_text(film, encoding="utf-8")
    (output / "project.json").write_text(json.dumps(local_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {at:g} 秒静音示例：{output}")
    print("project.json 是制作简报，修改后不会自动同步已生成的 HTML；保留已有工程，在新目录重建或直接编辑分镜。")
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", help="新工程目录")
    ap.add_argument("--config", default=str(ROOT / "examples" / "project.example.json"))
    args = ap.parse_args()
    try:
        create_project(args.output, args.config)
    except (ValueError, OSError) as exc:
        ap.exit(1, f"创建失败：{exc}\n")


if __name__ == "__main__":
    main()
