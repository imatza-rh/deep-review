# MR/PR Review Mode

> **Contents**: Data Fetching (Phase 0) — MR-Specific Phase 1 Steps — Phase 4.5 Auto-Draft — Completion Gate

Extracted phases and checks specific to Merge Request / Pull Request reviews.
Loaded when scope is an MR/PR (URL, `!N`, `#N`, or `mr N`).

## MR/PR Data Fetching (Phase 0)

Parse the input to extract platform and identifier:
- GitLab URL (`gitlab.*/merge_requests/N`) -> extract project path + iid
- GitHub URL (`github.com/org/repo/pull/N`) -> extract owner/repo + number
- `!N` or `mr N` -> GitLab MR in current project
- `#N` -> GitHub PR in current project

**Prerequisite check**: verify the required CLI tool is installed before proceeding.
For GitLab MRs: `which glab >/dev/null 2>&1` — if missing, report "glab CLI required
for GitLab MR reviews. Install: https://gitlab.com/gitlab-org/cli" and stop.
For GitHub PRs: `which gh >/dev/null 2>&1` — if missing, report "gh CLI required
for GitHub PR reviews. Install: https://cli.github.com/" and stop.

**Fetch metadata and diff in parallel:**

GitLab:
```bash
GITLAB_HOST=<host> glab mr view <iid> --output json   # metadata
git fetch origin merge-requests/<iid>/head:mr-<iid>    # branch for diff
GITLAB_HOST=<host> glab api "projects/<id>/merge_requests/<iid>/notes" --paginate  # comments
```

GitHub:
```bash
gh pr view <number> --json title,author,body,state,isDraft,files,labels,reviews
gh pr diff <number>
```

**CRITICAL: Use two-dot `git diff` scoped to changed files, NOT `glab mr diff` or three-dot.**
```bash
# Get changed files
CHANGED_FILES=$(git diff origin/<target>...mr-<iid> --name-only)

# Two-dot diff SCOPED to changed files (shows full changes including deletions)
git diff origin/<target>..mr-<iid> -- $CHANGED_FILES
git diff origin/<target>..mr-<iid> -- $CHANGED_FILES --stat
```

**Why two-dot scoped:**
- Three-dot (`...`) = merge-base diff = shows only additions, hides deletions/modifications
- Two-dot unscoped (`..`) = shows ALL differences including unrelated main branch changes
- Two-dot scoped (`.. -- <files>`) = shows the MR's FULL changes to its OWN files

`glab mr diff` and three-dot both hide regressions. A two-dot scoped diff reveals additions + deletions + modifications — the ONLY command that reliably shows regressions.

**Save diff for cross-model agents:**
```bash
DIFF_FILE=$(mktemp /tmp/pr-diff-XXXXXX)
git diff origin/<target>..mr-<iid> -- $(git diff origin/<target>...mr-<iid> --name-only) > "$DIFF_FILE"
```
All CLI agents reuse this file. If the diff is incomplete, ALL agents review incomplete data.

### Regression Detection Gate (MANDATORY)

```bash
git diff origin/<target>..mr-<iid> -- $(git diff origin/<target>...mr-<iid> --name-only) --numstat
```

**RENDERED GATE (mandatory before Phase 1):**
```
Regression check:
- Files with deletions: [list from --numstat where deletions > 0]
- Per file: [filename: +N -N]
- Existing code changed: [YES / NO - pure addition]
- If YES: trace each deletion for regression risk in Phase 1
```

## MR-Specific Phase 1 Steps

These execute alongside the standard Phase 1 steps.

### 1b. Verify the diff includes deletions and modifications

For GitLab MRs, confirm the diff source is `git diff` (not `glab mr diff`). If the Regression Detection Gate showed deletions/modifications:
- Read the BEFORE version (`git show origin/<target>:<file>`) and AFTER version side by side
- Trace each deleted line: was it dead code, or did something depend on it?
- Trace each modification: does the new version preserve all behaviors?
- For YAML/config: compare indentation — a key moved to a different level changes its semantic meaning entirely
- Check inheritance chains: if the change modifies a PARENT entity, identify ALL children that inherit from it

### 1c. Consumer impact check

For each file that was MODIFIED (not newly added), identify what consumes it:
- Job definitions, playbooks, or CI configs that reference the file
- Other roles/tasks that import or include the modified code
- Variables, environment blocks, or templates that the modified code provides

**RENDERED GATE:**
```
Consumer impact:
- <modified_file>: consumed by [list consumers] | behavior change: [YES: what / NO]
```

### 1d. Operational regression check

For changes to shared roles, libraries, or modules:
- **Callers**: grep for all `include_role`, `import_role`, `include_tasks`, function calls, imports
- **Variable flow**: for each new variable, verify it's set by the caller's preceding steps
- **Behavioral equivalence**: for each caller, does the modified code produce the same result?
- **New dependencies**: does the change introduce requirements the old code didn't have?

**RENDERED GATE:**
```
Operational regression:
- Callers: [list each with file:line]
- New dependencies: [list or "none"]
- Behavioral equivalence: [YES per caller / NO: what changed]
```

### 7b. Verify prior review comments

Fetch the user's own review comments on THIS MR/PR:
- GitHub: `gh api repos/{owner}/{repo}/pulls/{N}/comments` + `pulls/{N}/reviews`
- GitLab: `glab api "projects/{id}/merge_requests/{iid}/notes" --paginate` (paginate fully!)

For EACH prior comment:
- Read the ACTUAL code at the location — don't trust author replies
- Verify the fix matches the suggestion
- Check for side-effect regressions in the same commit

**RENDERED GATE (when prior reviews exist):**
```
Prior review verification:
| # | Comment | Addressed? | Evidence (tool call) |
|---|---------|-----------|---------------------|
| 1 | [summary] | YES code / YES reply / NO | [grep/Read that verified] |
```

### 12. Check submission metadata

- **Commit history**: count total commits, fix-on-fix ratio. >40% fix-on-fix = closer scrutiny needed
- **CI/gate status**: check gate job results. 0% pass rate = red flag
- **Review status**: count human (non-bot) reviews
- **Scope coherence**: do ALL changed files serve one purpose?
- **Draft status**: note if the MR is marked as draft
- **MR description quality**: compare description against actual diff. Flag misleading claims, missing testing evidence
- **Existing behavior changes**: for each MODIFIED file, check whether the description mentions the change
- **Depends-On format**: verify format matches CI system expectations
- **Testing evidence**: does description describe what was tested, where, with what results?

### 14. Upstream docs alignment

For MRs implementing features with upstream documentation:
- Fetch the relevant upstream doc and search for the feature keyword
- If docs EXIST: does the MR follow them? Flag deviations
- If docs are PARTIAL: flag the gap
- If docs DON'T EXIST: flag as process finding

## Phase 4.5: Auto-Draft Review

**Skip for non-MR reviews.** Only fire when the scope is an MR/PR.

### Reviewer role detection

**RENDERED GATE:**
```
Review format:
- User role: [REVIEWER (drafting for user) / AUTHOR (presenting to user)]
- Verdict: [APPROVE / COMMENT / REQUEST CHANGES]
- Format: [INLINE (default) / GENERAL (fallback)]
- Finding count: [N findings -> N inline comments, max 4]
```

**If AUTHOR**: Phase 4 report IS the deliverable. Offer to fix.
**If REVIEWER**: produce draft for the user to post.

### Inline comment rules

- One comment per finding, placed on the specific diff line
- Max 2-3 sentences each. Suggestive tone ("Consider..." not "Fix:")
- Only Warnings + Criticals. Drop Suggestions unless high-value
- Use `-` (hyphen) as separator, never em dash

### General comment for process findings

When Phase 1 step 12 produced process findings, auto-generate ONE general draft note summarizing them. Max 4-5 bullet points, suggestive tone.

### Posting mechanics

Create as a PENDING review:
- GitHub: `gh api repos/{owner}/{repo}/pulls/{N}/reviews --input <json>` — omit `event` field (defaults to PENDING)
- GitLab: `create_draft_note` per finding (draft notes are only visible to the author until submitted)

**Line positioning for GitLab inline comments:**
GitLab displays the THREE-DOT diff. Only ADDED lines are commentable inline. Parse the three-dot diff to find commentable lines:
```bash
glab api "projects/<id>/merge_requests/<iid>/diffs" | python3 -c "
import json, sys, re
for d in json.load(sys.stdin):
    f = d['new_path']
    nl, ol = 0, 0
    for line in d['diff'].split('\n'):
        if line.startswith('@@'):
            m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)', line)
            if m: ol, nl = int(m.group(1))-1, int(m.group(2))-1
            continue
        if line.startswith('+'): nl += 1; print(f'ADDED {f}:{nl}: {line[1:80]}')
        elif line.startswith('-'): ol += 1
        else: nl += 1; ol += 1
"
```

Notes on non-added lines render detached at the bottom of the diff — invisible to the author. Place them in the general note instead.

**Post-draft verification:**
```
Draft notes posted:
- Patchset: [same as analysis / NEW - findings updated]
- Inline: [N notes on added lines]
- General: [N notes]
- Total: [N posted, N verified via API]
```

### Post-approval housekeeping

After posting approval, check thread state and suggest resolution:
1. Fetch all review threads
2. Classify: RESOLVED / ADDRESSED (safe to resolve) / WAITING (leave open)
3. Present summary and resolve on confirmation

## Phase 1 Completion Gate (MR-specific additions)

```
Phase 1 complete (MR):
- [1c] Consumer impact: [checked / N/A / SKIPPED -> STOP]
- [1d] Operational regression: [checked / N/A / SKIPPED -> STOP]
- [7b] Prior reviews checked: [N points verified / none / SKIPPED -> STOP]
- [12] Description vs diff: [checked / SKIPPED -> STOP]
- [12] Depends-On format: [correct / informational only / N/A]
- [P0] Cross-model launched: [list or "Solo tier"]
```
Any SKIPPED -> go back and execute that step.
