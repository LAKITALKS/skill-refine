# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-07

**0.2.0 is a deliberate, breaking recalibration release.** The default measuring
stick in 0.1.0 was a private, hardcoded section schema that did not reflect
Agent Skills best practices. This release fixes that. Scores and JSON output
change on purpose; correctness was prioritized over backwards compatibility.

### Changed (BREAKING)

- **Default profile is now `standard`**, aligned with Agent Skills / `SKILL.md`:
  frontmatter `name` + `description` are required, and there is no forced section
  taxonomy. Scores for the same file will differ from 0.1.0.
- **JSON output is a new, versioned contract** (`schema_version: "2.0"`), shared
  by `check --json` and `report --format json`. Changes from 0.1.0:
  - top-level object (was a bare array) with `schema_version`, `tool`,
    `tool_version`, `profile`, `generated_at`, `skills`, and `summary`;
  - findings expose a stable `id` (renamed from `rule`) plus `severity`;
  - per-skill `score` is `{ total, components: { … } }` (was flat);
  - each skill reports `format` (`folder`/`flat`) and `skill_dir`;
  - smells are objects (`{ id, message }`).
- **`httpx` and `anthropic` are now optional extras**, not core dependencies.
  The core install (`check`/`report`/`restore`) is fully offline. `improve`
  requires `[llm]`, `[ollama]`, or `[anthropic]` and prints a friendly install
  hint (not a traceback) when they are missing.
- **`ScoreCard` no longer carries `llm_score`.** The optional LLM critique is a
  separate, independent number in the LLM layer (`--critique`).
- Package version is now single-sourced from `skill_refine/__init__.py`.

### Added

- **Folder-based Agent Skills**: `<skill-name>/SKILL.md` is discovered
  recursively; the directory name is the skill's identity. Legacy flat `.md`
  files remain supported.
- **Profiles**: built-in `standard` (default) and `strict` (the preserved 0.1
  schema), plus custom profiles loaded from TOML via
  `--profile ./profile.toml` (extend a built-in and override fields).
- **`--fail-on {never,warning,error}`** on `check` for CI exit codes.
- **Deterministic, offline lint core** in `skill_refine.lint`, importable and
  free of any LLM/provider/network imports (enforced by a dedicated test).
- **`lint_path(target, profile="standard") -> list[SkillReport]`** as the
  primary public API entry point (a convenience wrapper over `analyze`).
- **Recursive, bounded discovery**: folder `SKILL.md` and legacy flat `*.md`
  are found recursively (so `check examples/` finds `examples/skills/*.md`),
  while hidden/vendor dirs (`.git`, `.venv`, `node_modules`, `.archive`, …),
  a skill's own supporting files, common project docs, and trees deeper than
  5 levels are skipped.
- **Reference calibration fixtures** (`examples/reference/*/SKILL.md`) with a
  regression test asserting they score >= 8.0 with zero ERROR findings under
  the `standard` profile.
- **CI** (`.github/workflows/ci.yml`) running `pytest` and `ruff check .` on
  Python 3.11 and 3.12 for every push and pull request.

### Fixed

- **`improve` no longer silently uses the stub provider.** The stub echoes its
  input and produced a fake "improvement" when no real provider was available.
  Now the stub is never auto-selected; `improve` refuses with a non-zero exit
  and an explanation when no provider is configured, and `--provider stub`
  requires an explicit `--allow-stub` flag.
- **empty-section false positive**: a heading whose content lives in child
  subsections (or a fenced code block) is no longer reported as empty and no
  longer penalized in the structure score.

### Changed (architecture)

- Split into `skill_refine.lint` (offline core), `skill_refine.llm` (optional
  refinement layer), and a thin `skill_refine.cli` facade.
- A single analysis engine (`lint.analyze`) is shared by all commands, removing
  the previously duplicated parse→check→smell→score pipeline.
- The unified-diff helper moved to `skill_refine.textdiff` so `restore` never
  imports the LLM layer.

### Migration

- To reproduce 0.1.0 scoring and section expectations, pass `--profile strict`.
- Update any JSON consumers to read `schema_version` and the new structure
  (top-level object, `findings[].id`, `score.components`).
- If you use `improve`, install an extra: `pip install 'skill-refine[llm]'`
  (or `[anthropic]` / `[all]`).

## [0.1.0]

- Initial release: `check`, `improve`, `report`, `restore` over flat Markdown
  skill files with a private section schema and built-in `httpx` dependency.
