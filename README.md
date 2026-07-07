# skill-refine

A standard-aligned linter and optional refiner for **Agent Skills** (`SKILL.md`).

skill-refine treats skill files (Markdown with YAML frontmatter) as inspectable instruction artifacts. Its deterministic, offline **lint core** parses their structure, runs quality checks, detects recurring antipatterns ("skill smells"), and computes transparent, profile-driven scores. An **optional LLM layer** can then rewrite, complete, or patch a skill — every proposed change is shown as a diff and written only after explicit confirmation, with an automatic backup.

## What's new in 0.2.0

> **0.2.0 is a deliberate, breaking recalibration.** See [CHANGELOG.md](CHANGELOG.md).

- **Folder-based Agent Skills** (`<skill-name>/SKILL.md`) are first-class, discovered recursively. Legacy flat `.md` files are still supported.
- **Profiles.** The default is now `standard`, aligned with Agent Skills best practices (frontmatter `name` + `description` required, no forced section taxonomy). The old v0.1 schema is preserved as `--profile strict`. Custom profiles can be loaded from TOML.
- **Offline, dependency-clean lint core.** `skill_refine.lint` is importable, deterministic, and imports no LLM/network code. `httpx`/`anthropic` are now **optional extras**; `improve` shows a friendly message if they are missing.
- **Stable JSON schema (`schema_version: "2.0"`)** shared by `check --json` and `report --format json`.

## Install

```bash
pip install -e .                 # core only: check / report / restore (offline)
pip install -e ".[llm]"          # + Ollama (local models via httpx)
pip install -e ".[anthropic]"    # + Anthropic API
pip install -e ".[all]"          # everything
pip install -e ".[dev]"          # pytest + ruff for development
```

The core install has **no network dependencies**. Only `improve` needs an extra.

## Quick start

```bash
skill-refine check my-skill/            # a folder of Agent Skills
skill-refine check my-skill/SKILL.md    # a single folder skill
skill-refine check legacy-skill.md      # a legacy flat skill
skill-refine check skills/ --profile strict --json
skill-refine report my-skill/ --format json --output report.json
skill-refine improve my-skill/SKILL.md --dry-run   # needs an LLM extra
```

## Commands

### `check` — deterministic analysis

```bash
skill-refine check PATH                 # file, SKILL.md, or directory
skill-refine check PATH --profile strict
skill-refine check PATH --profile ./my-profile.toml
skill-refine check PATH --verbose
skill-refine check PATH --json          # schema 2.0
skill-refine check PATH --fail-on error # exit 1 if any error finding (CI)
```

Fully offline. Reports findings (with stable ids + severities), smells, and a 0–10 score with sub-scores for completeness, structure, metadata, and conciseness — all interpreted through the active profile.

### `report` — export analysis

```bash
skill-refine report PATH                              # Markdown to stdout
skill-refine report PATH --format json               # JSON (schema 2.0)
skill-refine report PATH --format md --output r.md
skill-refine report PATH --profile strict --format json
```

### `improve` — LLM-assisted refinement (optional layer)

```bash
skill-refine improve SKILL.md --mode all         # comprehensive rewrite
skill-refine improve SKILL.md --mode clarity     # clarity / compact / robustness / structure / safety
skill-refine improve SKILL.md --section warnings # patch one section
skill-refine improve SKILL.md --dry-run          # preview diff, write nothing
skill-refine improve SKILL.md --provider ollama  # anthropic / ollama / stub
skill-refine improve SKILL.md --critique         # add an independent LLM quality score
```

**Flow:** analyze → (optionally) generate missing sections → rewrite via LLM → guard validation → show before/after score + diff → confirm → backup → write. If the LLM extras are not installed, `improve` exits with an install hint (not a traceback).

### `restore` — restore from backup

```bash
skill-refine restore SKILL.md            # interactive selection
skill-refine restore SKILL.md --list
skill-refine restore SKILL.md --latest
```

Shows a diff before restoring and requires confirmation. Offline.

## Discovery

When you point a command at a **directory**, skill-refine finds:

- **Folder skills** — every `SKILL.md`, searched recursively. The skill's
  identity is its directory name.
- **Legacy flat skills** — other `*.md` files, also searched recursively, so
  `skill-refine check examples/` finds `examples/skills/*.md`.

To keep discovery predictable and safe, it **excludes**:

- markdown inside a folder-skill's own directory tree (treated as the skill's
  supporting files, not standalone skills);
- common project docs (`README.md`, `CHANGELOG.md`, `LICENSE.md`,
  `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`);
- hidden directories (any `.name`, e.g. `.git`, `.archive`) and heavy
  vendor/build directories (`.venv`, `venv`, `node_modules`, `dist`, `build`,
  `__pycache__`, …);
- anything deeper than 5 directory levels below the target.

Pointing a command at a **single file** always analyzes exactly that file.

## Profiles

| Profile | Intent |
|---------|--------|
| `standard` (default) | Agent Skills best practices: frontmatter `name` + `description` required, description-quality checks, no forced section taxonomy. |
| `strict` | The legacy v0.1 schema: eight expected sections (`description`, `when to apply`, `when not to apply`, `warnings`, `inputs`, `outputs`, `steps`, `examples`) and section-driven smells. |
| custom `.toml` | `--profile ./file.toml` — extends a built-in and overrides fields. |

Example custom profile:

```toml
name = "house-style"
extends = "standard"
max_total_words = 4000
expected_sections = ["overview", "steps"]
smells = ["TOKEN_BLOAT", "WALL_OF_TEXT"]

[weights]
metadata = 0.4
completeness = 0.2
```

## JSON output (schema 2.0)

`check --json` and `report --format json` emit the same versioned document:

```json
{
  "schema_version": "2.0",
  "tool": "skill-refine",
  "tool_version": "0.2.0",
  "profile": "standard",
  "generated_at": "2026-07-07T12:00:00Z",
  "skills": [
    {
      "path": "skills/pdf-filler/SKILL.md",
      "name": "pdf-filler",
      "format": "folder",
      "skill_dir": "skills/pdf-filler",
      "word_count": 41,
      "estimated_tokens": 54,
      "score": {
        "total": 10.0,
        "components": {
          "completeness": 10.0, "structure": 10.0,
          "metadata": 10.0, "conciseness": 10.0
        }
      },
      "findings": [
        { "id": "missing-frontmatter-description", "severity": "error",
          "message": "…", "section": null }
      ],
      "smells": [{ "id": "TOKEN_BLOAT", "message": "…" }],
      "verdict": "Solid — skill is well-structured and complete."
    }
  ],
  "summary": {
    "skill_count": 1,
    "avg_score": 10.0,
    "counts": { "error": 0, "warning": 0, "info": 0, "smell": 0 }
  }
}
```

## Python API

The offline lint core is importable and deterministic. The primary entry point
is `lint_path`:

```python
from skill_refine.lint import lint_path

# profile may be "standard" (default), "strict", or a path to a .toml profile
reports = lint_path("examples/", profile="standard")  # -> list[SkillReport]

for r in reports:
    print(r.name, r.skill_format, r.score.total)
    for f in r.findings:
        print(" ", f.severity.value, f.id, f.message)
```

`lint_path` returns a `list[SkillReport]`. Lower-level helpers (`analyze`,
`discover`, `load_profile`, `render_json`, `render_markdown`) are also exported.
Nothing in `skill_refine.lint` imports an LLM/provider/network dependency.

## Skill smells

| Smell | What it means | Active in |
|-------|---------------|-----------|
| `VAGUE_TRIGGER` | "When to apply" uses imprecise language | strict |
| `NO_WARNINGS` | No warnings/caveats | strict |
| `NO_FAILURE_CASES` | No "when not to apply" | strict |
| `NO_INPUTS_OUTPUTS` | Inputs/outputs not specified | strict |
| `NO_BOUNDARIES` | Neither apply nor not-apply boundary | strict |
| `EMPTY_FRONTMATTER` | Frontmatter missing entirely | strict |
| `TOKEN_BLOAT` | Exceeds the word budget | standard + strict |
| `WALL_OF_TEXT` | Oversized paragraphs without structure | standard + strict |

Smells are heuristic and require no LLM. Which smells fire is profile-dependent.

## LLM providers

`check`, `report`, and `restore` work with the core install. Only `improve` needs a provider (and the corresponding extra).

| Provider | Setup | Extra |
|----------|-------|-------|
| **Anthropic** | `export ANTHROPIC_API_KEY=sk-…` | `[anthropic]` |
| **Ollama** | `ollama serve` (local) | `[llm]` / `[ollama]` |
| **Stub** | built-in (echoes input) | — |

Auto-selection priority: Anthropic > Ollama > Stub.

## Backups

Every `improve` write creates a timestamped `.bak` next to the file (e.g. `SKILL.20260707_142315.bak`). Backups are never auto-deleted; use `restore`.

## Architecture

```
skill_refine/
  lint/   # offline, deterministic core — no httpx/anthropic/network imports
  llm/    # optional refinement layer (providers, rewrite, patch, critique, guard)
  cli/    # thin Typer facade
```

The offline guarantee is enforced by a test (`tests/test_lint/test_offline_isolation.py`).

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,all]"

pytest -q          # run tests
ruff check .       # lint
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
