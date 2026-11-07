# 美术风格：水墨「留白」+ 实拍「赤金墨韵」标注

以下是原项目选择的水墨留白方案，可作为新项目候选。示例中的片名、地点、年份和印章都要换成当前项目内容；它们不是通用要求。所有页面都用 `assets/ink.css`、`assets/kit.js`（`data-in/fade/out`、`data-reveal`、`data-vreveal`、`data-slide`、`data-pop`、`data-kb`、`data-type`、`data-draw`、`data-dip`、`data-r`、`data-move`、`data-span`）。

## 目录

1. 素材准备（字体、水墨纹理）
2. 宣纸页：片名、章节卡、史料相片、竖排引文、会议原文字卡、片尾、资料来源
3. 实拍标注：地点标签、楼名角框、毛笔关键词、讲述人字条
4. 尾声补救：人物入相框 + 旁边出字 + 整屏切史料
5. 转场
6. 字幕样式

## 1. 素材准备

- **字体**：按 [README](../README.md) 下载并配置可选的宋体与行书。`create_project.py` 会复制实际提供的字体，并生成 `shots/fonts.css`；页面先加载 `ink.css`，再加载 `fonts.css`。未配置时使用系统衬线字体，不能宣称它与原字体效果完全一致。
- **水墨纹理**：`python scripts/gen_ink.py <工程>/assets/ink` 生成宣纸、远山、深墨底、雾、笔触与红日。示例工程默认使用纯 CSS 背景，因此不需要提前生成纹理。将背景换为 `.coal` 时，保留相应图片的相对位置。

## 2. 宣纸页

**片名**（竖排毛笔，左上一轮小红日）：
```html
<body class="pp" data-len="4.6"><div class="coal"></div>
<img class="abs" src="../assets/ink/sun.png" style="left:328px;top:158px;width:184px;height:184px" data-in=".2" data-fade="1.2">
<div class="abs brush vert" style="left:1240px;top:150px;font-size:130px" data-vreveal=".4,1.8">片名示例</div>
<div class="abs serif vert grey" style="left:1130px;top:300px;font-size:32px;letter-spacing:12px" data-in="1.9">副标题</div>
<div class="seal" style="left:1400px;top:890px;width:62px;height:62px;font-size:22px" data-pop="2.5,.35,1.6">小<br>组</div>
```

**章节卡**：标题行写“第 一 章”，中间是大号毛笔副题（2 到 4 个字效果最好），下面一行用宋体写章名，右边配一枚序号印章（壹、贰、叁、肆），再加一轮缓慢下沉的小红日。印章的横坐标按 `960 + 字数 × 字号 / 2 + 24` 计算，否则会压到字。

**史料相片**：使用 `.print`，照片放在左边或居中；右边写毛笔年份和宋体说明，配一枚两字小印章（例如“向东”）。照片原来是什么颜色就保留什么颜色，不要强行转黑白（原项目偏好；新项目按自己的选择）。

**竖排引文**：`writing-mode:vertical-rl`，宋体 52px，`line-height:110px`，逐字打出（`data-type`）。左侧竖排写落款，下方配“预言”这类两字印章。

**会议原文字卡**：只放原文和出处，不要垫楼、塑像这类和会议无关的实景照片（避免画面暗示错误的史实关联）。

**片尾**：先是“谢谢观看”（毛笔 96px），下面依次是组名和主讲人、拍摄、讲稿、剪辑各一行（宋体 42px）。**资料来源单独做成最后一页**，接在片尾之后停 7 秒，分“影像资料、历史照片、文字史实、其他”四类，类名用朱红。

## 3. 实拍标注（赤金墨韵）

- **地点标签**：顶部加一条渐变压暗带，保证白字可读。左上角放当前组名的小印章，旁边是宋体地点，从左侧滑入，显示约 4 秒。
  ```html
  <div class="abs" style="left:0;right:0;top:0;height:300px;background:linear-gradient(180deg,rgba(20,4,3,.45),rgba(20,4,3,.15) 55%,transparent)"></div>
  <div class="seal" style="left:96px;top:84px;width:52px;height:52px;font-size:20px" data-pop=".3,.35,1.6">小<br>组</div>
  <div class="abs serif" style="left:166px;top:84px;font-size:34px;letter-spacing:6px;color:#f4ece0;text-shadow:0 2px 10px rgba(0,0,0,.65)" data-slide=".4,.8,-24,0">校园 · 当前拍摄地点</div>
  ```
- **楼名角框**：说到楼名的那一刻，用金色线条（`#e0bf7c`，4px）描出四个角，再从下方滑出一条红底宋体标签，例如“二〇二一年 由‘计算机楼’更名”。角框坐标在原片全景的那一帧上量。
- **毛笔关键词**：一次只放一个词，用 `.brushk`，2 到 4 个字，字号 140 到 180。两个词时错开排成两行，旁边可以加一枚年份印章。放在画面的空白处：先抽出那一帧看清人物在哪，不要压住人头和身体。
- **讲述人字条**：左下角刷一笔红色飞白（`brush_red.png`，或用 SVG 加粗糙滤镜画），上面写“讲述人”和组名。
- **不要做的事**：不要在人物旁边放半透明黑底加多行小字的说明框。这是原风格的取舍；若当前用户另有要求则按其要求。

## 4. 尾声补救（出镜画面差、背景杂、低头念稿时）

1. 先做一条底片：宣纸加远山作底，相框只在原片有人物的时段淡入淡出；用颜色占比找出人物时段。
   - 相框：16px 木框（由深到浅渐变），外加 34px 卡纸和一条金线。
   - 取景：从原片截一条约 560×970 的竖条，以人脸为中心（先抽帧打网格量出人脸横坐标）。
   - 调色：保持彩色，只压一点饱和度并略微调暖（`eq=saturation=0.82,colorbalance=rm=0.03:bm=-0.03`），**不要转黑白**。
2. 相框右侧（x≈800 起）随讲述逐条出字：
   - 毛笔序号“壹、贰、叁”，配一个毛笔关键词，再加一两行宋体。
   - 每一组用一个容器包住，按台词时间控制进出（`data-in` / `data-out`）。
   - `data-reveal` 不会自己退场，容器不包住的话，上一条会和下一条叠在一起。
3. 讲到关键句时整屏切换宣纸史料页，例如“1952 年数学系”“1976 年计算机系成立”“计算机楼 → 王湘浩楼”“两个名字”。
4. 整屏页出现之前，要让侧栏文字先退场，否则侧栏会压在整屏页上面（OpenFilm 的前置轨道在上，以轨道顺序控制）。

## 5. 转场

- 宣纸页之间：墨点晕开，用 SVG 圆加 `feTurbulence` 和 `feDisplacementMap`，配合 `data-r` 把半径从 0 放大到 1350，再用 `data-dip` 退场。
- 实拍和实拍之间：直接硬切，这是纪录片的惯例。
- **不要留空档**：镜头之间哪怕只空 0.1 秒，渲染出来也是纯黑，观众会觉得“闪了一下”。可先修时间线，再用 `scripts/fill_black_export.py` 检查与补短黑场；有意保留的黑场需单独核对。

## 6. 字幕样式

新版 OpenFilm 使用 WebVTT 与时间线字幕轨道，按安装版能力和样片效果调整。白字在宣纸上可用较粗深褐描边，例如颜色 `#2a1f19`，先在实拍和浅色背景各抽一帧确认对比度。

原项目使用 `.film/subtitles.json`，不再作为新版默认写法；也不要无条件向渲染命令追加旧的 `--subtitles` 参数。具体路由见 [工具参考](tools.md)。
