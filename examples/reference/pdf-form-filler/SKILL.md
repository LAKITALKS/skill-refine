---
name: pdf-form-filler
description: Fills the AcroForm fields of a PDF from a JSON field map and optionally flattens the result
---

## Overview

This skill populates the interactive form fields (AcroForm) of a PDF document using
a JSON object that maps field names to values, then writes a new PDF. It can leave
the form editable or flatten it so the values become permanent, non-editable content.

## When to use

- The user has a fillable PDF and a set of values to place into its fields.
- The user wants to generate many filled PDFs from one template and structured data.

## Inputs

- Path to the source PDF (must contain an AcroForm).
- A JSON object mapping field names to string, number, or boolean values.
- An optional `flatten` flag (defaults to false).

## Steps

1. Load the PDF and read its form field names.
2. Validate the JSON map against those names; report any unknown fields.
3. Apply each value to its field, coercing types as needed.
4. If `flatten` is set, flatten the form so values are baked into the page.
5. Write the result to a new file, never overwriting the source template.

## Warnings

- Fail loudly on unknown field names rather than silently dropping data.
- Flattening is irreversible; keep the original template untouched.
