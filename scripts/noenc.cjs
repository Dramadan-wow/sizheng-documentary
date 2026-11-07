// 让 OpenFilm 看不到显卡编码器,渲染时改用它自带的 x264(CRF 16)。只改本进程里 `ffmpeg -encoders` 的输出。
const cp = require('child_process');
const orig = cp.execFile;
cp.execFile = function (file, args, ...rest) {
  if (Array.isArray(args) && args.includes('-encoders')) {
    const i = rest.findIndex((x) => typeof x === 'function');
    if (i >= 0) {
      const cb = rest[i];
      rest[i] = (err, stdout, stderr) => cb(err, String(stdout).split('\n').filter((l) => !/_(amf|qsv|nvenc|mf|vaapi|d3d12va|videotoolbox)\b/.test(l)).join('\n'), stderr);
    }
  }
  return orig.call(this, file, args, ...rest);
};
require('module').syncBuiltinESMExports();
