---
name: git-commit-writer
description: Writes a Conventional Commits message from the currently staged git diff, inferring type and scope
---

## Overview

This skill turns the staged changes in a git repository into a single, well-formed
Conventional Commits message. It infers the commit type (feat, fix, docs, refactor,
test, chore) and an optional scope from the files and hunks that are staged, then
produces a concise subject line and an informative body.

## When to use

- The user has staged changes (`git add`) and asks for a commit message.
- The user wants their history to follow the Conventional Commits convention.

## Inputs

- The output of `git diff --staged` (required).
- Optionally, the repository's recent `git log` for style consistency.

## Steps

1. Read the staged diff and group changes by intent.
2. Choose a single primary type; pick a scope only when one clearly dominates.
3. Write a subject line in the imperative mood, no trailing period, <= 72 chars.
4. Add a body that explains the "why" when the change is non-trivial.
5. Present the message for review; never commit without explicit confirmation.

## Example

For a staged change that adds retry logic to an HTTP client:

```
feat(http): retry idempotent requests on transient failures

Adds a bounded exponential backoff to GET/HEAD requests so intermittent
5xx responses no longer surface as hard errors to callers.
```
