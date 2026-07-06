---
name: format-check
description: >
  Fast zero-token format check on an academic paper using local rule engines.
  Use when the user says "check format", "格式检查", "查格式", "看看格式对不对",
  "run format check", "format only" — accepts .tex and .docx files.
  Does NOT consume API tokens.
argument-hint: "[path/to/paper.tex|.docx]"
user-invocable: true
references:
  - knowledge/formats/latex-rules.md
  - knowledge/formats/docx-rules.md
  - knowledge/formats/common-errors.md
---

# Format Check Skill

Quick, zero-token format check using local rule engines.

## Workflow

1. Run `article-check format <path>` for raw rule-engine results
2. Run `article-check template auto-detect --paper <path>` if template detection is needed
3. Present results to user grouped by severity

## Output Format

```
📐 Format Check Report for: paper.tex
   Template: IEEE Transactions (auto-detected)
   File type: latex

🔴 Critical (0)
🟡 Major (2)
  - Missing section: Reference
  - Document class 'article' should be 'IEEEtran'
🟢 Minor (3)
  - No page numbers
  - Font not set to Times New Roman
  - Missing package: graphicx
ℹ️ Info (1)
  - $$ at line 24 should be \[...\]

Total: 6 issues | 0 critical | 2 major | 3 minor | 1 info
```

## Constraints
- This is a read-only check — no file modifications
- Results are from local rules only; no API tokens consumed
- For deeper review, use the paper-review skill
