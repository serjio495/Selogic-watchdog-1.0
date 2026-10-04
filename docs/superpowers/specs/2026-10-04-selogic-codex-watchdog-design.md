# SELOGIC Codex Watchdog Design

## Goal
Provide Codex with a low-cost, local completion guard that catches common omissions before a coding task ends, while escalating to an independent reviewer only when risk justifies the context cost.

## Architecture
A portable Agent Plugin bundles one workflow skill and lifecycle hooks. `UserPromptSubmit` records the task and risk score; `PostToolUse` records verification evidence; `Stop` inspects the repository and can request exactly one additional Codex pass. The reviewer workflow is instruction-driven and uses Codex multi-agent capability when available rather than an external API.

## Modes
- light: deterministic checks only.
- smart: deterministic checks plus reviewer guidance for materially complex work.
- strict: deterministic checks plus reviewer requirement for code changes.

## Deterministic findings
- changed code with no observed test command;
- likely secrets added in the diff;
- real `.env` changed;
- missing reviewer evidence when required;
- selected config/doc mismatches in strict mode.

## Safety and cost controls
The hook never edits files and never makes network calls. Reviewer usage is gated by mode and complexity. `stop_hook_active` prevents recursive completion loops.

## Success criteria
The package validates as JSON, all unit tests pass, hook scripts require only Python standard library, and Stop can block once with a clear `YOU SHOULD KNOW` report.
