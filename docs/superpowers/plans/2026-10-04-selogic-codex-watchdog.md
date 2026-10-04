# SELOGIC Codex Watchdog Implementation Plan

> **For agentic workers:** implement with test-first changes and verify the whole package before release.

**Goal:** Build a local Codex plugin that performs evidence-based completion checks and supports optional independent review.

**Architecture:** One standard-library Python hook handles lifecycle events and persists minimal state in `PLUGIN_DATA`. A skill defines reviewer behavior and cost-aware mode rules. Portable and compatibility manifests expose the package to Codex.

**Tech Stack:** Python 3 standard library, JSON, Markdown, Codex Agent Plugins lifecycle hooks.

**Spec:** `docs/superpowers/specs/2026-10-04-selogic-codex-watchdog-design.md`

## Tasks

- [x] Define tests for mode loading, complexity, test-command observation, secret detection, Stop blocking and loop prevention.
- [x] Implement hook state machine and git evidence collection.
- [x] Add plugin manifests and lifecycle hook configuration.
- [x] Add Watchdog skill and reviewer contract.
- [x] Add local marketplace/install documentation.
- [x] Run final package validation and integration probes.
- [x] Produce distributable ZIP.
