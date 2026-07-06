# Meta-Review Prompt

Synthesize the individual reviewer reports into a single meta-review.

For each finding:
- If all reviewers agree, state it as confirmed
- If reviewers disagree, note the disagreement
- Assign an overall score (0.0 - 1.0)

Structure:
1. **Summary** (2-3 sentences)
2. **Strengths**
3. **Major Concerns** (with severity)
4. **Minor Issues**
5. **Overall Assessment**
6. **Recommendation**: Accept / Minor Revision / Major Revision / Reject
