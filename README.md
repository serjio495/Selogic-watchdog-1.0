# SELOGIC Codex Watchdog

Codex completion guard inspired by the "you should know" pattern. It adds deterministic lifecycle checks plus an optional independent reviewer workflow.

## What v0.1 does

- scores a prompt for risk/complexity;
- in `smart`/`strict`, injects reviewer guidance when warranted;
- records whether a test command was observed;
- inspects the final git diff for likely committed secrets;
- warns when code changed without observed tests;
- in strict mode requires independent review evidence;
- uses the Codex `Stop` hook to request one extra pass, avoiding an infinite loop via `stop_hook_active`.

No external API or paid service is required. The hook is Python standard library only.

## Modes

Create `.codex/watchdog.json` in a project:

```json
{"mode":"light"}
```

or `smart` (default), or `strict`.

You can also set `SELOGIC_WATCHDOG_MODE=light|smart|strict`.

## Install locally

### Personal plugin

1. Copy this folder to `~/.codex/plugins/selogic-codex-watchdog`.
2. Create or update `~/.agents/plugins/marketplace.json` with the entry from `marketplace.example.json`.
3. Restart the ChatGPT desktop app / Codex local client.
4. Install/enable `SELOGIC Codex Watchdog` from your local marketplace.
5. Review and trust the bundled hook definition when Codex asks. Plugin hooks are intentionally not auto-trusted.

### Repo-scoped plugin

Copy the plugin to `<repo>/plugins/selogic-codex-watchdog` and add an entry to `<repo>/.agents/plugins/marketplace.json` using source path `./plugins/selogic-codex-watchdog`.

Then the repo may enable it in `.codex/config.toml`:

```toml
[plugins."selogic-codex-watchdog@local-repo"]
enabled = true
```

## Optional multi-agent support

For independent reviewer subagents, Codex multi-agent support must be enabled in your local Codex configuration:

```toml
[features]
multi_agent = true
```

Watchdog remains useful without multi-agent support because the lifecycle hook checks still run.

## Validate package

```bash
python3 -m unittest discover -s tests -v
python3 -m json.tool plugin.json >/dev/null
python3 -m json.tool hooks/hooks.json >/dev/null
```

## Limitations

- Hooks cannot reliably prove semantic test coverage; they can only observe commands and inspect repository evidence.
- Secret scanning is intentionally conservative and heuristic, not a substitute for a dedicated scanner.
- Public plugin submission currently has restrictions around packages containing lifecycle hooks; this package is primarily for local/repo use.
