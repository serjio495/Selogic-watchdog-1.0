---
name: watchdog
description: Use during coding, refactoring, debugging, migrations, API/auth changes, deployment work, or other repository modifications to independently check completion evidence before finishing.
---

# SELOGIC Codex Watchdog

Treat completion as an evidence check, not a confidence statement.

## Modes

Read the project mode from `.codex/watchdog.json` when present. Valid values:

- `light`: deterministic hook checks only. Do not spawn a reviewer solely for Watchdog.
- `smart`: use a reviewer for materially complex work when multi-agent support is available.
- `strict`: require an independent reviewer for any code change when multi-agent support is available.

Default mode is `smart`.

## Reviewer trigger

In `smart`, prefer a reviewer when the task touches three or more risk domains such as database/schema, API, auth/permissions, deployment/CI, architecture/refactor, or security. Also use judgment for broad multi-file changes where a shipped mistake is expensive.

In `strict`, review every code-changing task.

Do not spawn a reviewer for trivial text-only edits or when multi-agent tools are unavailable. Hooks still perform deterministic checks.

## Reviewer contract

The reviewer is read-only. Give it the original task, relevant changed files/diff, and verification evidence. Ask it to report only actionable findings under these headings:

1. Requirement coverage
2. Regression risk
3. Tests and verification
4. Security and secrets
5. Scope creep
6. Docs/config/migrations

The reviewer must not edit files. It should end with exactly one line:

- `REVIEWER: PASS` when no material issue remains, or
- `REVIEWER: FAIL` when at least one material issue remains.

If the reviewer fails, fix confirmed issues and re-review only the affected surface.

## Completion evidence

Before claiming completion:

- run the relevant tests for changed code;
- run the project-level test command when practical;
- inspect the final diff;
- confirm migrations/config/env examples/docs when interfaces or configuration changed;
- never claim green verification if a command was not run or failed;
- surface pre-existing failing tests explicitly rather than hiding them.

The Stop hook may request one additional pass with a `YOU SHOULD KNOW` report. Address each item or state why it is not applicable, then finish again.
