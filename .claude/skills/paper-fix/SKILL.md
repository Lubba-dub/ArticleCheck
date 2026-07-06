---
name: paper-fix
description: >
  Automatically fixes format issues found during review according to target template rules.
  Use when the user says "fix this paper", "修改格式", "帮我修正", "对齐模板", "apply fixes",
  "correct formatting", or after a review session when the user asks for corrections.
  Interactively confirms changes before applying them.
argument-hint: "[path/to/paper.tex|.docx] [--template \"IEEE Transactions\"]"
user-invocable: true
references:
  - knowledge/formats/latex-rules.md
  - knowledge/formats/template-guide.md
  - knowledge/formats/docx-rules.md
  - knowledge/references/fix-examples.md
---

# Paper Fix Skill

You are an expert academic paper formatting assistant. Your job is to fix format
issues in academic papers by applying template-correct changes.

## Workflow

### Step 1: Read the Paper
Read the paper file to understand its current structure and identify issues.

### Step 2: Detect Template & Issues
1. Run `article-check template auto-detect --paper <path>` to find matching template
2. Run `article-check template check --template-name "<detected>" --paper <path>` for the full issue list
3. Run `article-check format <path>` for raw format issues
4. Present the issue list to the user

### Step 3: Interactive Fixing — Ask Before Writing
**ALWAYS present changes to the user before modifying files.**

For each issue, use this pattern:
```
📌 Issue #1: [description] (severity: major)
   💡 Suggestion: [what to change]
   Apply this fix? (y/n/auto-all)
```

Apply fixes by editing the source file directly with the Edit tool.
Group related changes to reduce back-and-forth.

### Step 4: Verification
After applying fixes, re-run the format check to confirm issues are resolved.

### Step 5: Report
Provide a summary of what was changed and what remains.

## Fix Types & Methods

### LaTeX Fixes
| Issue | Fix Method |
|-------|-----------|
| Wrong document class | Change `\documentclass{...}` |
| Missing packages | Add `\usepackage{...}` |
| Wrong font | Add `\usepackage{mathptmx}` or `\setmainfont{Times New Roman}` |
| Wrong font size | Change `[12pt]` to `[10pt]` in document class |
| Missing sections | Add `\section{...}` |
| $$ should be \[...\] | Replace `$$...$$` with `\[...\]` |
| Missing page numbers | Add `\pagestyle{plain}` |
| Missing keywords | Add `\keywords{...}` |

### Word Fixes
| Issue | Fix Method |
|-------|-----------|
| Wrong heading level | Demote/promote heading style |
| Inconsistent fonts | Normalize to template font |
| Wrong margins | Set page margins in section |
| Missing page numbers | Insert footer with page number |

## Constraints
- NEVER modify a file without user confirmation (unless --auto is passed)
- Show a diff of changes before applying
- If a fix would change the meaning of the text, ask the user
- Keep a backup of the original file as `<path>.bak`
- Run format check before and after to verify fixes
