# Re-Review Mode (Phases R0-R4)

Activated by `--re-review`, `--follow-up`, or natural language detection
("addressed", "verify the comments", "check if fixed", "is it ready after fixes?").

Re-review REQUIRES an MR/PR reference — "verify the changes" without an MR
number defaults to standard review of uncommitted work.

**Skips**: Phase -1, Phase 1 steps 2-14, Phase 1.5, Phase 2, Phase 2.5 (full perspective sweep).
**Keeps**: MR metadata fetch, branch checkout, full file read, domain context search.

**Scope gate:**
```
Scope: re-review (--follow-up) - [N] files in MR, [K] files in fix commit(s), +[X] -[Y] lines incremental
```

## Phase R0: Load Prior Review State

1. Fetch ALL discussion threads on the MR (paginate fully — `per_page=100`, follow until null)
2. Filter threads:
   - **Our comments** (filter by current username) — primary verification targets
   - **Other reviewer comments** (human, non-bot) — secondary verification
   - **Bot/system notes** — skip
3. For EACH thread, extract: original comment text, file:line, resolution status, author reply
4. Fetch commit history to identify fix commits after our review:
   - Find our LATEST review comment timestamp
   - `git log --after="<timestamp>" mr-<iid>` for fix commits
   - **Amend workflow detection**: if the MR has only 1 commit, the author uses amend-and-force-push. No separate fix commits exist. Verify with `git cat-file -t <head_sha>` — if it fails, the old SHA was amended away. Fall back to full MR diff vs main.
   - **Force-push/rebase**: if review SHA is orphaned AND branch has multiple commits, fall back to timestamp-based diff.
5. Get the incremental diff:
   - **Normal workflow**: `git diff <our_review_sha>..mr-<iid> -- <changed_files>`
   - **Amend workflow**: `git diff origin/main..mr-<iid> -- <changed_files>` (full diff)
   - **Rebase**: same as amend

6. **Submission state check** — 3 items that CHANGE between reviews:
   a. **CI gate status**: check if CI is configured (`ls .github/workflows/*.yml` or `test -f .zuul.yaml`). If configured, check pass/fail. If not configured, record "CI: not configured (manual gate)" — NOT a blocker.
   b. **Commit history hygiene**: count commits, check for sensitive data keywords
   c. **Fix commit scope audit**: compare files in fix commits against files from our review comments. Files changed beyond review scope = bundled changes.

**Zero-comment guard**: if no prior human review found, STOP and suggest full review instead.

**RENDERED GATE (blocks Phase R1):**
```
Re-review state:
- Our comments: [N threads - M resolved, K unresolved]
- Other reviewers: [N comments from <names>]
- Author workflow: [AMEND / FIXUP / REBASE]
- Fix commits: [N since review / "amend - no fix trail"]
- Incremental diff: [+N -M lines across K files / "full MR diff (amend)"]
- CI status: [N passed, M failed / not configured / 0 triggered]
- Git history: [clean / SENSITIVE DATA: what]
- Bundled changes: [none / N files beyond scope]
```

## Phase R1: Verify Each Comment (CORE)

For EACH of our prior review comments, execute ALL 6 steps:

1. **Read original comment** — what we asked, which file:line, what fix expected
2. **Read code NOW** — `Read()` the targeted file:line. This is EVIDENCE. Author replies are CLAIMS.
3. **Verify fix in code** — does current code match suggestion? Use grep/sed/Read for evidence
4. **Read author reply** — does explanation match code? If approach changed, verify the new approach handles the original concern
5. **Side-effect check** — did the fix change MORE than asked? Did it remove definitions other code depends on?
6. **Regression check** — for each consumer of changed code, verify the fix doesn't break downstream
7. **Cross-repo dependency re-check** — for dependencies flagged in original review OR in MR description `Depends-On:`, re-check current state: MERGED / STILL OPEN / ABANDONED / CHANGED SCOPE

**Classification per comment:**
- **ADDRESSED** — code change matches suggestion, verified with tool call
- **ADDRESSED DIFFERENTLY** — different approach that solves the concern
- **PARTIALLY ADDRESSED** — some aspects fixed, others missed
- **ACKNOWLEDGED** — author declined with valid reasoning
- **SILENTLY IGNORED** — no code change, no reply
- **REGRESSED** — fix introduced a new problem

**RENDERED GATE (blocks Phase R2):**
```
Comment verification:
| # | Comment summary | Status | Evidence (tool call) | Side effects |
|---|----------------|--------|---------------------|--------------|
| 1 | [what we asked] | ADDRESSED | Read L45: [code shows] | none |
| 2 | [what we asked] | PARTIALLY | grep: A fixed, B missed | removed Y defn |
```

## Phase R2: Verify Other Reviewers' Comments

Same 6-step verification for OTHER reviewers' threads. Prioritize by severity if 10+ threads.

## Phase R3: Incremental Analysis (agent-assisted)

Dispatch agents on the INCREMENTAL diff to catch new issues in fix commits:

| Incremental size | Agents | Families |
|-----------------|--------|----------|
| <20 lines | 1 Claude + 1 cross-model | 2 |
| 20+ lines | 3+ agents | 2+ |

Agent prompt: "These fix commits address review feedback. Check: (1) are fixes correct, (2) do they introduce NEW problems, (3) did any fix over-scope?"

**Cross-model is mandatory even for re-review.** If Gemini fails, try Codex, then Cursor, then Bob. Only declare "CROSS-MODEL UNAVAILABLE" after all families fail.

**RENDERED GATE:**
```
R3 cross-model:
- [model]: [OK: N findings / FAILED: error / SKIPPED (prior succeeded)]
- Non-Claude families with results: [N - if 0 -> show all errors]
```

## Phase R3.5: Self-Confidence Gate (blocks R4)

```
Re-review confidence:
- What I'm NOT confident about: [list - empty on 5+ comments = suspect]
- What I didn't check: [list - must include non-code items]
- Merge-readiness beyond code: [CI? History? Scope?]
- What would the AUTHOR say is wrong: [prediction]
```

**Investigate gaps immediately** — each item triggers a tool call BEFORE proceeding.

**Claim verification table (mandatory for READY/APPROVE):**
```
| # | Claim | Tool call evidence | Certain? |
|---|-------|-------------------|----------|
| 1 | "All N comments addressed" | R1 table: N/N ADDRESSED | YES/NO |
| 2 | "No regressions" | R3 agents: 0 regressions | YES/NO |
| 3 | "CI is clean" | check: N passed / 0 ran | YES/NO |
| 4 | "History clean" | git log -S: no secrets | YES/NO |
```
Any NO -> investigate before verdict.

## Phase R4: Verdict & Actions

| Verdict | Condition | Action |
|---------|-----------|--------|
| **READY** | All addressed/acknowledged, no regressions, R3.5 all YES | Resolve threads + approve |
| **ALMOST** | Most addressed, 1-2 minor gaps, or non-code blockers | Gap summary, keep threads open |
| **NOT READY** | IGNORED or REGRESSED comments, or new issues | Per-comment status, request changes |

**Pre-verdict checklist:**
```
Pre-verdict:
- R0 CI: [value] | R3.5 matches? [Y/N]
- R0 history: [value] | R3.5 matches? [Y/N]
- R0 bundled: [value] | R3.5 matches? [Y/N]
- R1 comments: [N/M] | R3.5 matches? [Y/N]
- R3 agents: [findings] | R3.5 matches? [Y/N]
```

**Draft MR guard**: if MR is still draft, READY resolves threads but does NOT approve.

**On READY**: present verdict + proposed actions. Wait for user confirmation before any API calls.

**Report format:**
```
## Re-Review: [MR title]

| Metric | Value |
|--------|-------|
| Verdict | READY / ALMOST / NOT READY |
| Comments verified | N / M |
| CI status | [value] |
| Git history | [clean / issue] |

### Per-Comment Verification
[table from R1]

### Other Reviewers
[table from R2]

### Fix Commit Analysis
[agent findings from R3]

### Actions
[thread resolutions, approval status, remaining gaps]
```
