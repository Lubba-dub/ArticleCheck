---
name: reference-verify
description: >
  Verifies references in an academic paper — checks count, format, and key-reference
  existence via DOI/arXiv lookup. Use when the user says "check references",
  "文献审查", "查引用", "verify citations", "参考文献检查", "检查引用格式".
argument-hint: "[path/to/paper.tex|.docx] [--check-doi]"
user-invocable: true
references:
  - knowledge/references/citation-styles.md
  - knowledge/references/doi-guide.md
---

# Reference Verification Skill

## Workflow

### Step 1: Extract References
- For LaTeX: count `\bibitem` entries, extract titles, DOIs if present
- For Word: scan bibliography section

### Step 2: Check Against Template
- Compare count against the detected template's min/max reference requirements
- Check citation style (numeric vs author-year) matches template

### Step 3: Key Reference Verification
Ask the user which references to verify, or auto-verify if `--check-doi`:

1. Extract DOIs from the reference list
2. Use `article-check` reference tools to verify DOI existence
3. Flag missing or suspicious references

### Step 4: Report

```
📚 Reference Check Report
   Total references: 32
   Template minimum: 15 ✅

📌 Format: IEEE numeric style ✅
📌 DOI check: 28/32 have DOIs, 4 missing
📌 Key refs verified: 5/5 exist ✅
📌 Citation accuracy: check each claim manually

⚠️ Issues:
  - Ref #12: No DOI found
  - Ref #23: Year appears inconsistent with original
```

## Constraints
- Never fabricate a verification result
- Clearly label "verified via API" vs "unverifiable (no DOI)"
- For non-verifiable refs, suggest manual check
