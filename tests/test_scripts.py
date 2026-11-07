"""Regression tests; neural models are replaced with small fakes, never downloaded."""
import copy
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
import uuid
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TEMP_PARENT = os.environ.get("SIZHENG_TEST_TMP")
sys.path.insert(0, str(ROOT / "scripts"))
from create_project import create_project, validate_config
from runtime import find_binary
from fill_black_export import blacks, probe


@contextmanager
def temporary_directory(prefix="documentary-test-"):
    if not TEMP_PARENT:
        with tempfile.TemporaryDirectory(prefix=prefix) as directory:
            yield directory
        return
    # Some restricted Windows tokens cannot re-enter tempfile's mode-0700 ACL.
    # An explicitly supplied workspace test root uses its inherited permissions.
    parent = Path(TEMP_PARENT).resolve()
    directory = parent / (prefix + uuid.uuid4().hex)
    directory.mkdir()
    try:
        yield str(directory)
    finally:
        if directory.resolve().parent != parent:
            raise RuntimeError("Unexpected test cleanup path")
        shutil.rmtree(directory)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory(prefix="documentary-tests-")
        self.root = Path(self.temp.__enter__())
        self.addCleanup(self.temp.__exit__, None, None, None)
        self.config = json.loads((ROOT / "examples/project.example.json").read_text(encoding="utf-8"))

    def save(self):
        path = self.root / "project.json"
        path.write_text(json.dumps(self.config, ensure_ascii=False), encoding="utf-8")
        return path

    def test_project_is_self_contained_and_escapes_text(self):
        self.config["title"] = '<script>alert("title")</script>'
        target = create_project(self.root / "中文 工程", self.save())
        page = (target / "shots/title.html").read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn('<script>alert("title")</script>', page)
        self.assertTrue((target / "shots/kit.js").is_file())
        film = (target / "film.html").read_text(encoding="utf-8")
        self.assertIn('at="8"', film)
        self.assertNotIn("http://", film)

    def test_existing_project_is_preserved(self):
        target = create_project(self.root / "film", self.save())
        original = (target / "film.html").read_bytes()
        with self.assertRaisesRegex(ValueError, "不是空目录"):
            create_project(target, self.save())
        self.assertEqual(original, (target / "film.html").read_bytes())

    def test_font_paths_are_relative_to_config(self):
        (self.root / "font.ttf").write_bytes(b"test-font-payload")
        self.config["fonts"]["brush"] = "font.ttf"
        target = create_project(self.root / "film", self.save())
        self.assertEqual((target / "assets/fonts/ZhiMangXing.ttf").read_bytes(), b"test-font-payload")
        generated = json.loads((target / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(generated["fonts"]["brush"], "assets/fonts/ZhiMangXing.ttf")

    def test_bad_constraints_are_rejected(self):
        for field, value in (("min_live_action_ratio", 70), ("max_external_ratio", float("nan")), ("duration_seconds_min", -1)):
            config = copy.deepcopy(self.config)
            config["requirements"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_config(config)


class RuntimeTests(unittest.TestCase):
    def test_explicit_binary_wins_over_environment(self):
        with temporary_directory() as directory:
            explicit = Path(directory) / "中文 tool.exe"
            explicit.write_bytes(b"not-executed")
            with mock.patch.dict(os.environ, {"FFMPEG_BINARY": "missing-tool-for-test"}):
                self.assertEqual(find_binary("ffmpeg", str(explicit)), str(explicit.resolve()))

    def test_invalid_explicit_binary_does_not_fall_back(self):
        with self.assertRaises(FileNotFoundError):
            find_binary("ffmpeg", "nonexistent-documentary-test-binary")


class NarrationTests(unittest.TestCase):
    def test_reference_embedding_is_unpacked_before_scoring(self):
        spec = importlib.util.spec_from_file_location("documentary_tts_test", ROOT / "scripts/tts_voice.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules = {name: ModuleType(name) for name in (
            "torch", "librosa", "faster_whisper", "speechbrain", "speechbrain.inference",
            "speechbrain.inference.classifiers", "speechbrain.utils", "speechbrain.utils.fetching",
        )}
        modules["faster_whisper"].WhisperModel = lambda *a, **k: SimpleNamespace(
            transcribe=lambda *a, **k: ([SimpleNamespace(text="一九七七年")], {})
        )
        modules["speechbrain.inference.classifiers"].EncoderClassifier = SimpleNamespace(from_hparams=lambda **k: object())
        modules["speechbrain.utils.fetching"].LocalStrategy = SimpleNamespace(COPY="copy")
        embedding, audio = np.array([1.0, 0.0]), np.zeros(16000, dtype=np.float32)
        with mock.patch.dict(sys.modules, modules), mock.patch.object(module.sf, "read", return_value=(audio, 16000)), mock.patch.object(module.Checker, "emb", return_value=(embedding, audio)):
            checker = module.Checker("reference.wav", cache_dir="unused-test-cache")
            self.assertIs(checker.R, embedding)
            similarity, accuracy, _ = checker.score(audio, 16000, "1977年")
        self.assertAlmostEqual(similarity, 1.0)
        self.assertAlmostEqual(accuracy, 1.0)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg, cls.ffprobe = find_binary("ffmpeg"), find_binary("ffprobe")
        except OSError as exc:
            raise unittest.SkipTest(str(exc))

    def setUp(self):
        self.temp = temporary_directory(prefix="documentary-video-")
        self.root = Path(self.temp.__enter__()) / "中文 路径"
        self.addCleanup(self.temp.__exit__, None, None, None)
        self.root.mkdir()

    def make_video(self, name, duration=3, expression=None, audio=False):
        path = self.root / name
        cmd = [self.ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=red:s=160x90:r=25:d={duration}"]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}"]
        if expression:
            cmd += ["-vf", f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='{expression}'"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        cmd += ["-c:a", "aac"] if audio else ["-an"]
        subprocess.run(cmd + [str(path)], check=True, capture_output=True)
        return path

    def run_export(self, source, destination, *options, expect=0):
        cmd = [sys.executable, "-X", "utf8", str(ROOT / "scripts/fill_black_export.py"), str(source), str(destination),
               "--ffmpeg", self.ffmpeg, "--ffprobe", self.ffprobe, *map(str, options)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def test_short_gap_is_fixed_at_25fps_without_input_audio(self):
        source = self.make_video("原片.mp4", expression="between(t,0.4,0.48)")
        self.assertTrue(blacks(source, self.ffmpeg))
        target = self.root / "成片.mp4"
        self.run_export(source, target, "--fps", 25)
        self.assertFalse(blacks(target, self.ffmpeg))
        self.assertTrue(probe(target, self.ffprobe)[1])
        self.assertAlmostEqual(probe(target, self.ffprobe)[0], 3, delta=0.1)

    def test_long_and_leading_black_are_preserved(self):
        source = self.make_video("black.mp4", duration=4, expression="between(t,0,0.12)+between(t,1,1.8)", audio=True)
        target = self.root / "kept.mp4"
        self.run_export(source, target, "--fps", 25)
        kept = blacks(target, self.ffmpeg)
        self.assertTrue(any(start == 0 for start, end in kept))
        self.assertTrue(any(end - start > 0.6 for start, end in kept))

    def test_tail_gap_is_fixed_and_silent_tail_can_follow_audio(self):
        source = self.make_video("source.mp4", duration=3, audio=True)
        tail = self.make_video("tail.mp4", duration=3, expression="between(t,0.4,0.48)")
        target = self.root / "joined.mp4"
        self.run_export(source, target, "--tail", tail, "--split", 1, "--fps", 30)
        self.assertFalse(blacks(target, self.ffmpeg))
        self.assertAlmostEqual(probe(target, self.ffprobe)[0], 4, delta=0.1)

    def test_existing_output_is_not_overwritten(self):
        source = self.make_video("source.mp4")
        target = self.root / "existing.mp4"
        target.write_bytes(b"keep-me")
        self.run_export(source, target, expect=1)
        self.assertEqual(target.read_bytes(), b"keep-me")


if __name__ == "__main__":
    unittest.main()
