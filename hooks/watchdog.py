#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

VALID_MODES = {"light", "smart", "strict"}
CODE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".kts",
    ".php", ".rb", ".cs", ".cpp", ".c", ".h", ".hpp", ".swift", ".vue", ".svelte",
}
TEST_PATTERNS = [
    r"(^|\s)pytest(\s|$)", r"(^|\s)python\s+-m\s+pytest(\s|$)",
    r"(^|\s)npm\s+(run\s+)?test(\s|$)", r"(^|\s)pnpm\s+(run\s+)?test(\s|$)",
    r"(^|\s)yarn\s+test(\s|$)", r"(^|\s)bun\s+test(\s|$)",
    r"(^|\s)go\s+test(\s|$)", r"(^|\s)cargo\s+test(\s|$)",
    r"(^|\s)dotnet\s+test(\s|$)", r"(^|\s)mvn\s+test(\s|$)",
    r"(^|\s)gradle\w*\s+test(\s|$)", r"(^|\s)phpunit(\s|$)",
]
COMPLEXITY_TERMS = {
    "database": ["database", "db", "база", "миграц", "schema", "схема"],
    "api": ["api", "endpoint", "эндпоинт", "rest", "graphql"],
    "auth": ["auth", "oauth", "jwt", "авторизац", "аутентификац", "permission", "роль"],
    "deploy": ["deploy", "деплой", "docker", "kubernetes", "terraform", "ci/cd", "pipeline"],
    "architecture": ["архитект", "refactor", "рефактор", "subsystem", "микросервис"],
    "security": ["security", "безопасн", "secret", "credential", "уязвим"],
}
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key)\s*[:=]\s*['\"]([^'\"]{12,})['\"]"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
]
PLACEHOLDERS = {"changeme", "example", "your-token-here", "your_api_key", "dummy", "placeholder"}


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def read_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=2, check=False
        )
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_root() -> Path:
    here = Path.cwd()
    out = run_git(["rev-parse", "--show-toplevel"], here).strip()
    return Path(out) if out else here


def load_mode(root: Path) -> str:
    env_mode = os.getenv("SELOGIC_WATCHDOG_MODE", "").strip().lower()
    if env_mode in VALID_MODES:
        return env_mode
    cfg = root / ".codex" / "watchdog.json"
    if cfg.exists():
        try:
            mode = json.loads(cfg.read_text(encoding="utf-8")).get("mode", "smart")
            if isinstance(mode, str) and mode.lower() in VALID_MODES:
                return mode.lower()
        except (OSError, json.JSONDecodeError):
            pass
    return "smart"


def state_path(data_dir: Path) -> Path:
    return data_dir / "state.json"


def read_state(data_dir: Path) -> dict[str, Any]:
    path = state_path(data_dir)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(data_dir: Path, state: dict[str, Any]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp = state_path(data_dir).with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(state_path(data_dir))


def complexity_score(prompt: str) -> tuple[int, list[str]]:
    text = prompt.lower()
    reasons: list[str] = []
    for label, terms in COMPLEXITY_TERMS.items():
        if any(term in text for term in terms):
            reasons.append(label)
    if len(prompt) > 1000:
        reasons.append("long-prompt")
    return len(reasons), reasons


def is_test_command(command: str) -> bool:
    return any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in TEST_PATTERNS)


def scan_security_text(text: str) -> list[str]:
    findings: list[str] = []
    for line in text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        lowered = line.lower()
        if any(ph in lowered for ph in PLACEHOLDERS):
            continue
        if any(pattern.search(line) for pattern in SECRET_PATTERNS):
            findings.append("В diff похожий на секрет credential. Проверь и убери его из репозитория.")
            break
    return findings


def repo_snapshot(root: Path) -> dict[str, Any]:
    changed = run_git(["diff", "--name-only", "HEAD"], root).splitlines()
    untracked = run_git(["ls-files", "--others", "--exclude-standard"], root).splitlines()
    files = sorted(set(x.strip() for x in [*changed, *untracked] if x.strip()))
    diff = run_git(["diff", "--no-ext-diff", "--unified=0", "HEAD"], root)
    return {"changed_files": files, "diff": diff}


def code_changed(files: list[str]) -> bool:
    return any(Path(f).suffix.lower() in CODE_SUFFIXES for f in files)


def docs_changed(files: list[str]) -> bool:
    return any(Path(f).suffix.lower() in {".md", ".rst", ".txt"} or "docs/" in f for f in files)


def build_findings(mode: str, state: dict[str, Any], changed_files: list[str], diff: str) -> list[str]:
    findings: list[str] = []
    changed_code = code_changed(changed_files)
    if changed_code and not state.get("test_commands"):
        findings.append("Изменён код, но Watchdog не увидел запуска тестов. Запусти релевантный test suite.")
    findings.extend(scan_security_text(diff))
    if any(Path(f).name in {".env", ".env.local", ".env.production"} for f in changed_files):
        findings.append("Изменён реальный .env-файл. Проверь, что секреты не попали в git; предпочитай .env.example.")
    if mode in {"smart", "strict"} and state.get("complexity_score", 0) >= 3 and not state.get("review_completed"):
        findings.append("Задача выглядит сложной, но независимый reviewer ещё не отмечен завершённым.")
    if mode == "strict" and changed_code and not state.get("review_completed"):
        findings.append("Strict mode требует independent review перед завершением изменения кода.")
    if mode == "strict" and changed_code and not docs_changed(changed_files):
        if any(Path(f).name.lower() in {"config.py", "settings.py", "package.json", "pyproject.toml", "dockerfile"} for f in changed_files):
            findings.append("Изменена конфигурационная поверхность без сопутствующей документации. Проверь README/docs/env example.")
    return _dedupe(findings)


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def review_prompt(mode: str, score: int, reasons: list[str]) -> str:
    basis = ", ".join(reasons) if reasons else "несколько изменений"
    strict = " Review обязателен перед завершением." if mode == "strict" else ""
    return (
        f"SELOGIC Watchdog: режим {mode}, complexity={score} ({basis}). "
        "Для сложной задачи используй независимого reviewer-subagent, если multi-agent доступен. "
        "Reviewer не должен редактировать код: он проверяет соответствие исходной задаче, regressions, tests, security, scope и docs. "
        "После review явно отметь в рабочем контексте, что review completed." + strict
    )


def handle_user_prompt(event: dict[str, Any], root: Path, data_dir: Path, mode: str) -> dict[str, Any]:
    prompt = str(event.get("prompt") or "")
    score, reasons = complexity_score(prompt)
    state = {
        "prompt": prompt,
        "complexity_score": score,
        "complexity_reasons": reasons,
        "test_commands": [],
        "tool_events": 0,
        "review_completed": False,
    }
    write_state(data_dir, state)
    if mode == "light":
        return {"continue": True}
    threshold = 3 if mode == "smart" else 1
    if score >= threshold:
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": review_prompt(mode, score, reasons),
            }
        }
    return {"continue": True}


def handle_post_tool(event: dict[str, Any], root: Path, data_dir: Path, mode: str) -> dict[str, Any]:
    state = read_state(data_dir)
    state["tool_events"] = int(state.get("tool_events", 0)) + 1
    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    command = ""
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or "")
    if tool_name.lower() in {"bash", "shell", "local_shell"} and command and is_test_command(command):
        tests = list(state.get("test_commands") or [])
        if command not in tests:
            tests.append(command)
        state["test_commands"] = tests
    response_text = json.dumps(event.get("tool_response") or "", ensure_ascii=False)
    if "review completed" in response_text.lower() or "reviewer: pass" in response_text.lower():
        state["review_completed"] = True
    write_state(data_dir, state)
    return {"continue": True}


def handle_stop(event: dict[str, Any], root: Path, data_dir: Path, mode: str) -> dict[str, Any]:
    if bool(event.get("stop_hook_active")):
        return {"continue": True}
    state = read_state(data_dir)
    snapshot = repo_snapshot(root)
    findings = build_findings(mode, state, snapshot["changed_files"], snapshot["diff"])
    if not findings:
        return {"continue": True}
    reason = "YOU SHOULD KNOW\n\n" + "\n".join(f"{idx}. {item}" for idx, item in enumerate(findings, 1))
    reason += "\n\nИсправь подтверждённые проблемы или явно объясни, почему конкретный пункт неприменим, затем заверши задачу повторно."
    return {"decision": "block", "reason": reason, "systemMessage": "SELOGIC Watchdog запросил дополнительную проверку."}


def main() -> int:
    event = read_event()
    root = repo_root()
    plugin_data = Path(os.getenv("PLUGIN_DATA") or os.getenv("CLAUDE_PLUGIN_DATA") or (root / ".codex" / ".watchdog-data"))
    mode = load_mode(root)
    event_name = str(event.get("hook_event_name") or event.get("event_name") or "")
    if event_name == "UserPromptSubmit":
        out = handle_user_prompt(event, root, plugin_data, mode)
    elif event_name == "PostToolUse":
        out = handle_post_tool(event, root, plugin_data, mode)
    elif event_name == "Stop":
        out = handle_stop(event, root, plugin_data, mode)
    elif event_name == "SessionStart":
        out = {"systemMessage": f"SELOGIC Codex Watchdog active ({mode})."}
    else:
        out = {"continue": True}
    emit(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
