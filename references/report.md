# Report Template & Formatting

## Template

Use this format. Omit any section with no content.

```
# Deep Review: [brief scope description]

| Metric | Value |
|--------|-------|
| Scope | [what was reviewed - branch, commit range, files] |
| Files reviewed | N |
| Lines changed | +A / -B |
| Findings | X critical, Y warnings, Z suggestions |
| Verdict | BLOCK / REVIEW / CLEAN |

## Files (include for 3+ files)

| File | Risk | Reason |
|------|------|--------|
| `path/to/file.py` | high | handles auth tokens |
| `path/to/other.py` | low | config value change |

## Critical

### 1. [one-line: impact + location] `confirmed`

**`file.py:42`** - [what breaks, leaks, or degrades]

**Data flow:** `user_input -> parse_request:12 -> db_query:42` (security findings only)

[code block showing problematic code]

**Fix:**
[code block showing suggested fix]

---

## Warnings

### 1. [one-line description] `confirmed|likely|verify[, runtime-needed]`

**`file.py:88`** - [impact]

[evidence: code snippet, trace, or explanation]

**Fix:** [recommendation]

---

## Suggestions

- **`file.py:120`** - [description]. [recommendation].

## Design [only when Phase -1 ran]

### Assessment: [SOUND / QUESTIONABLE / REVIEW-NEEDED]

[1-2 sentence summary]

- `[design]` **[file:line]** - [design concern]

## Questions

- **`file.py:55`** - [genuine uncertainty needing author input]

## Test Gaps

- [ ] [specific untested scenario] - **Impact**: [what bug would this prevent?] - **Criticality**: [high/medium/low]

## Notable

- [1-3 things done well. Skip if nothing stands out.]

## Submission [MR/PR only]

- **Commits**: N total, N% fix-on-fix. [Squash needed / OK]
- **Gate**: N/M passes. [Investigate / Pre-existing / N/A]
- **Scope**: [Coherent / Mixed - suggest splitting]
- **Reviews**: N human reviews in N days.

## Verified

- [dimension]: [what was checked and confirmed correct]

## Methodology

- **Strategy**: [single-pass | parallel agents | triage by risk]
- **Files analyzed**: N of M (N% coverage). [Skipped files and why]
- **Models**: [list families used]
- **Perspectives dispatched**: [P1-P7 code | C1-C9 content | "skipped (reason)"]
- **Confidence**: [high - full context | medium - diff + key files | low - diff only]
- **Not checked**: [dimensions or files NOT reviewed]
```

## Verdict Criteria

- **BLOCK** - any confirmed Critical. Merging would cause security breach, data loss, or crash.
- **REVIEW** - Warnings needing human judgment. Add urgency: "(address before merge)" or "(before release)"
- **CLEAN** - no issues or only Suggestions.

## Findings Cap

Max 10 for diff reviews, max 20 for MR/PR reviews and audit mode. If you exceed
the cap, re-apply severity calibration and keep the highest-signal findings. Process
findings don't count toward the cap.

## Path to CLEAN

When verdict is BLOCK or REVIEW, add a summary table:

```
## Path to CLEAN

| # | Severity | File:Line | Fix |
|---|----------|-----------|-----|
| 1 | Critical | `auth.py:42` | Add input validation for token parameter |
| 2 | Warning | `config.py:18` | Pin dependency version |
```

Omit if verdict is CLEAN.

## Audit Mode

When scope is a full repo or broad directory:

1. **Negotiate scope** for repos over 200 files - suggest: recently changed files,
   security-critical modules, or high-churn files
   (`git log --format='' --name-only | sort | uniq -c | sort -rn | head -20`)
2. **Project assessment** - community files, CI/CD gates, test infrastructure, docs quality
3. **Parallel agents** - for 10+ files, dispatch per-dimension agents. See `agents.md`
4. **Multi-perspective output** - when role-based views requested, organize by role. Deduplicate.

## Re-Review Verdict Criteria

When running in re-review mode (`--re-review`):

- **READY** - all comments addressed/acknowledged, no regressions. Action: resolve + approve
- **ALMOST** - most addressed, 1-2 minor gaps. Action: gap summary, keep threads open
- **NOT READY** - IGNORED or REGRESSED comments. Action: per-comment status, request changes

See `re-review.md` for the full re-review report template.
