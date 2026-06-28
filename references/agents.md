# Agent Prompt Templates

> **Contents**: Dispatch Rules — Per-File Review Agent — Cross-File Interaction Agent — Verification Agent — Aggregation

When the diff exceeds 10 files or 500 lines, spawn parallel subagents to review
high-risk files independently.

## Dispatch Rules

- **Max 5 agents** per batch — group files by module/feature if more need deep review
- Low-risk files (config changes, version bumps, comment-only) don't get agents
- Each agent gets the full file context, not just the diff

## Per-File Review Agent

```
You are reviewing `{file_path}` as part of a larger code change.

## Context
- Change type: {change_type} (new feature / bug fix / refactor / config / dependency)
- Project conventions: {conventions_summary}
- Commit message: {commit_message}
- Tech stack defenses: {existing_defenses}

## Your diff
{diff_content}

## Full file
Read the full file at `{file_path}` for surrounding context.

## Task
Analyze this change for:
1. **Correctness** — trace all code paths, check edge cases, verify code matches intent.
   Compare how the author handles the same concern in DIFFERENT parts of this change.
   Check if the change makes existing code comments inaccurate (comment rot).
2. **Security** — trace external inputs from entry to sink (write explicit data-flow
   paths). Check injection, auth bypass, secret exposure, SSRF, IDOR. For each finding:
   model the attacker, write the concrete exploit, rate trivial/moderate/difficult.
3. **Error handling** — what happens when dependencies fail or return unexpected data?
4. **Performance** — O(n^2) in hot paths? unbounded collections? resource leaks?

For each potential finding:
- Construct a concrete triggering scenario
- Check if the framework/library already handles this
- If you can't construct a trigger, do NOT report it

## Filtering
Do NOT flag:
- Pre-existing issues not made worse by this change
- Linter/compiler territory
- Style preferences without project convention backing
- Issues on unchanged lines

## Output
### Findings
For each: **file:line** — description (`confirmed`/`likely`/`verify`)
- **Impact**: what breaks
- **Data flow**: source -> ... -> sink (security findings)
- **Evidence**: the code path or input that triggers it
- **Fix**: specific recommendation

### Verified
What you checked and confirmed correct.

### Test Gaps
Specific untested scenarios.

If you find nothing, return "CLEAN" with what you verified.
```

## Cross-File Interaction Agent

After per-file agents complete, check cross-file interactions:

```
You are checking for cross-file interaction issues in a change spanning {N} files.

## Per-file findings
{aggregated_findings_from_other_agents}

## Changed files
{list_of_changed_files}

## Task
Check for issues that only emerge from the combination of changes:
1. **API contract mismatches** — does file A call file B with the right arguments?
2. **State consistency** — shared state assumptions still valid after both changed?
3. **Import/dependency cycles** — did the changes create circular dependencies?
4. **Migration ordering** — do schema/config changes need specific ordering?

Grep for cross-file references between changed files to verify contracts.

## Output
Return only cross-file findings. Do not repeat per-file findings.
```

## Verification Agent

Dispatch for every **Critical** finding and for **Warnings** below `confirmed` confidence.

```
You are a verification agent. Your ONLY job is to try to disprove this finding.
You succeed when you disprove it. You are not looking for more bugs.

## Finding to verify
{finding_description}

## Claimed evidence
{evidence_from_reviewer}

## Relevant code
Read: `{file_path}`

## Disproval checklist
Try each before confirming:
1. **Framework/library defense** — does the framework already handle this?
2. **Upstream validation** — input validation earlier in the call chain?
3. **Intentional behavior** — does git history indicate this is deliberate?
4. **Existing tests** — do tests cover this path?
5. **Overstated scope** — if "duplicated N times," diff the copies for intentional variation.
6. **Concrete trigger** — can you construct the input/sequence? If conditions can't co-occur, invalid.

## Output
Return exactly one of:
- **CONFIRMED** — I tried to disprove and failed. [what you checked]
- **DISPROVED** — [specific defense that invalidates the finding]
- **DOWNGRADE** — finding is real but severity should be lower. [reason]
- **ESCALATE** — finding is worse than stated. [explanation]
```

## Aggregation

After all agents report:
1. Merge findings, deduplicate overlaps
2. Tag perspective findings with `[perspective:P1]` through `[perspective:P7]`
3. Tag content findings with `[content:C1]` through `[content:C9]`
4. Re-apply self-audit checklist to aggregated findings
5. Run Verification Agent on each Critical and non-confirmed Warning
6. Identify systemic patterns — "4 modules have the same antipattern" = one systemic finding
7. Build unified report in Phase 4 format
