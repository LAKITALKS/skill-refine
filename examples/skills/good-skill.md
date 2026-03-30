---
name: Code Review
description: Perform a thorough code review on a pull request
tags:
  - code-review
  - quality
  - collaboration
---

## Description

This skill guides the assistant through performing a structured code review.
It covers checking for correctness, readability, performance, and security
concerns in the submitted code changes.

## When to apply

- When a user asks for a code review on a pull request or diff
- When reviewing code changes before merging
- When a teammate requests feedback on their implementation

## When not to apply

- When the user just wants code written, not reviewed
- When the code is a quick prototype not intended for production
- When the user explicitly says they don't want review feedback

## Warnings

- Do not block merges for stylistic preferences alone
- Be constructive, not dismissive
- Consider the author's experience level

## Inputs

- A pull request URL, diff, or code snippet
- Optional: repository context or coding standards document

## Outputs

- A structured review with categorized feedback (bugs, style, performance, security)
- Severity ratings for each finding
- Suggested fixes where applicable

## Steps

1. Read the full diff to understand the scope of changes
2. Identify the purpose of the change from the PR description or commit messages
3. Check for correctness: logic errors, edge cases, missing error handling
4. Check for readability: naming, structure, comments where needed
5. Check for performance: unnecessary allocations, N+1 queries, blocking calls
6. Check for security: injection risks, auth checks, data exposure
7. Summarize findings with actionable suggestions

## Examples

**Input:** "Please review this Python function that parses user input"

**Output:** A structured review noting input validation gaps, suggesting
type hints, and flagging a potential injection vector in the string
interpolation on line 42.
