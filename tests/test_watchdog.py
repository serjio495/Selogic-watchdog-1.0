import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

import watchdog


class WatchdogTests(unittest.TestCase):
    def test_mode_defaults_to_smart(self):
        with patch.dict(os.environ, {}, clear=True):
            with tempfile.TemporaryDirectory() as td:
                self.assertEqual(watchdog.load_mode(Path(td)), "smart")

    def test_mode_reads_project_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = root / ".codex" / "watchdog.json"
            cfg.parent.mkdir(parents=True)
            cfg.write_text('{"mode":"strict"}', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(watchdog.load_mode(root), "strict")

    def test_prompt_complexity_detects_architectural_work(self):
        score, reasons = watchdog.complexity_score(
            "Добавь миграцию базы, новый API endpoint, авторизацию и деплой"
        )
        self.assertGreaterEqual(score, 3)
        self.assertTrue(reasons)

    def test_test_command_detection(self):
        self.assertTrue(watchdog.is_test_command("pytest -q"))
        self.assertTrue(watchdog.is_test_command("npm test"))
        self.assertFalse(watchdog.is_test_command("git status"))

    def test_sensitive_diff_detection_avoids_placeholders(self):
        findings = watchdog.scan_security_text(
            '+ API_KEY="sk-proj-abcdefghijklmnopqrstuvwxyz123456"\n'
            '+ EXAMPLE_TOKEN="changeme"\n'
        )
        self.assertTrue(any("секрет" in f.lower() for f in findings))
        self.assertFalse(any("changeme" in f.lower() for f in findings))

    def test_stop_blocks_once_when_changed_code_has_no_tests(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / "plugin-data"
            data.mkdir()
            watchdog.write_state(data, {
                "prompt": "Исправь backend",
                "complexity_score": 2,
                "complexity_reasons": ["backend"],
                "test_commands": [],
                "tool_events": 3,
            })
            event = {
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": "Готово",
            }
            with patch.object(watchdog, "repo_snapshot", return_value={
                "changed_files": ["src/app.py"],
                "diff": "+print('x')\n",
            }):
                out = watchdog.handle_stop(event, root, data, "smart")
            self.assertEqual(out.get("decision"), "block")
            self.assertIn("YOU SHOULD KNOW", out.get("reason", ""))
            self.assertIn("тест", out.get("reason", "").lower())

    def test_stop_does_not_loop_when_already_active(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / "plugin-data"
            data.mkdir()
            watchdog.write_state(data, {"test_commands": []})
            event = {"hook_event_name": "Stop", "stop_hook_active": True}
            with patch.object(watchdog, "repo_snapshot", return_value={
                "changed_files": ["src/app.py"], "diff": "+x\n"
            }):
                out = watchdog.handle_stop(event, root, data, "smart")
            self.assertNotEqual(out.get("decision"), "block")

    def test_strict_requires_review_for_code_change(self):
        state = {"review_completed": False, "test_commands": ["pytest"]}
        findings = watchdog.build_findings(
            mode="strict",
            state=state,
            changed_files=["src/app.py"],
            diff="+x\n",
        )
        self.assertTrue(any("review" in f.lower() for f in findings))


if __name__ == "__main__":
    unittest.main()
