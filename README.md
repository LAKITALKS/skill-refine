# skill-refine

A local-first static analysis and refinement engine for agent skill files.

skill-refine treats skill files (Markdown with YAML frontmatter) as inspectable instruction artifacts. It parses their structure, runs deterministic quality checks, detects recurring antipatterns ("skill smells"), computes transparent scores, and — optionally — uses an LLM to rewrite, complete, or patch them. Every proposed change is shown as a diff and written only after explicit user approval.

## Quick Start

```bash
pip install -e .

# Analyze a skill
skill-refine check my-skill.md

# Analyze a directory
skill-refine check skills/

# Improve a skill (requires LLM provider)
skill-refine improve my-skill.md --dry-run

# Export a report
skill-refine report my-skill.md --format md --output report.md

# Restore from backup
skill-refine restore my-skill.md --list
```

## Commands

### `check` — Static analysis

```bash
skill-refine check skill.md              # Single file
skill-refine check skills/               # Directory (summary table)
skill-refine check skill.md --verbose    # Full detail
skill-refine check skill.md --json       # Machine-readable output
```

Runs deterministic checks without any LLM dependency: missing or empty sections, incomplete frontmatter, oversized paragraphs, and heuristic smell detection. Outputs a score (0–10) with sub-scores for completeness, structure, metadata, and conciseness.

### `improve` — LLM-assisted refinement

```bash
skill-refine improve skill.md                        # Full rewrite (mode: all)
skill-refine improve skill.md --mode clarity          # Improve clarity and precision
skill-refine improve skill.md --mode compact          # Reduce verbosity
skill-refine improve skill.md --mode robustness       # Add warnings, edge cases
skill-refine improve skill.md --mode structure        # Fix structure, generate missing sections
skill-refine improve skill.md --mode safety           # Strengthen safety guidance
skill-refine improve skill.md --section warnings      # Patch a single section
skill-refine improve skill.md --generate-missing      # Generate missing sections explicitly
skill-refine improve skill.md --dry-run               # Preview diff without writing
skill-refine improve skill.md --provider anthropic    # Select provider
skill-refine improve skill.md --critique              # Include LLM quality score
```

**Flow:** analyze → generate missing sections (if applicable) → rewrite via LLM → guard validation → show before/after score + diff → ask for confirmation → create backup → write.

### `report` — Export analysis reports

```bash
skill-refine report skill.md                           # Markdown to stdout
skill-refine report skill.md --format json             # JSON to stdout
skill-refine report skill.md --format md --output r.md # Write to file
skill-refine report skills/ --format json              # Directory report
```

Reports contain: file path, rule score, sub-scores, findings, smells, recognized sections, token estimates, and a verdict.

### `restore` — Restore from backup

```bash
skill-refine restore skill.md              # Interactive backup selection
skill-refine restore skill.md --list       # List available backups
skill-refine restore skill.md --latest     # Restore most recent backup
```

Shows a diff between the current file and the selected backup before restoring. Requires confirmation.

## Skill Smells

skill-refine introduces a practical vocabulary for recurring quality problems in skill files. These "skill smells" make instruction defects easier to spot, discuss, and fix systematically:

| Smell | What it means |
|-------|---------------|
| `VAGUE_TRIGGER` | "When to apply" uses imprecise language ("when needed", "as appropriate") |
| `NO_WARNINGS` | No warnings or caveats defined |
| `NO_FAILURE_CASES` | No "when not to apply" section |
| `TOKEN_BLOAT` | Skill exceeds reasonable token budget |
| `NO_INPUTS_OUTPUTS` | Inputs and outputs are not specified |
| `NO_BOUNDARIES` | Neither "when to apply" nor "when not to apply" exists |
| `WALL_OF_TEXT` | Paragraphs exceed word threshold without structure |
| `EMPTY_FRONTMATTER` | YAML frontmatter is missing entirely |

Smells are detected heuristically and do not require an LLM.

## LLM Providers

skill-refine is BYO model (bring your own). The `check`, `report`, and `restore` commands work without any provider. Only `improve` requires an LLM.

| Provider | Setup | Notes |
|----------|-------|-------|
| **Anthropic** | `export ANTHROPIC_API_KEY=sk-…` | Cloud API. Install: `pip install 'skill-refine[anthropic]'` |
| **Ollama** | `ollama serve` | Local models, no API key needed |
| **Stub** | Built-in | Returns content unchanged, for pipeline testing |

Auto-selection priority: Anthropic > Ollama > Stub.

## Scoring

The rule-based score (0–10) is a weighted average of four components:

| Component | Weight | Measures |
|-----------|-------:|----------|
| Completeness | 35% | Presence and non-emptiness of expected sections |
| Structure | 25% | Section count, empty sections, oversized sections |
| Metadata | 15% | Frontmatter fields: name, description, tags |
| Conciseness | 25% | Total word count relative to budget |

An optional LLM score (`--critique`) provides an independent 0–10 rating. Rule score and LLM score are always shown separately.

Token counts throughout the tool are **heuristic estimates** (~1.33x word count), not exact tokenizer output.

## Backups

Every `improve` write creates a timestamped `.bak` file next to the original:

```
my-skill.20250330_142315.bak
```

Backups are never deleted automatically. Use `skill-refine restore` to list and restore them.

## Known Limitations

- `improve` operates on single files (no batch mode)
- Section patching (`--section`) returns unchanged content for files with duplicate heading names
- The stub provider is for pipeline testing only
- LLM output quality depends on the model and provider used
- Token estimates are approximate

## Responsible use and validation

skill-refine is designed to help users inspect, improve, and maintain skill files locally. It may suggest structural changes, rewrites, or missing sections, but these outputs should always be reviewed carefully and validated in the user's own environment.

This tool is provided as-is, without guarantees of correctness, safety, compliance, or suitability for a particular use case. Users remain responsible for testing, validation, and responsible downstream use.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pip install pytest ruff

pytest tests/ -v          # Run tests
ruff check src/           # Lint
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
