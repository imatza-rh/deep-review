---
name: deep-review
description: "Deep code review with verification - correctness, security, performance, and robustness analysis. ALWAYS use this skill when the user mentions: reviewing code, checking changes, auditing a file or directory, verifying a commit, 'is this safe to merge', 'review my last commit', 'check my changes', 'deep review', 'audit this', 'make sure it's secure', 'look for bugs', or any request to thoroughly examine code for correctness, security, performance, or quality. Also triggers on: 'review staged changes', 'pre-commit check', reviewing specific files or directories, commit ranges, 'what I changed today', security audits, and verifying refactors didn't break anything. For MR/PR reviews: 'deep review MR', 'thorough review', 'should this merge', 'is this MR safe'. NOT for quick MR/PR glances - use a lighter review skill for those."
argument-hint: "[scope: staged | last commit | last N commits | file/dir path | commit range | MR/PR URL | !N | #N | --design]"
user_invocable: true
allowed-tools: [Read, Glob, Grep, Agent, Skill, Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(git blame:*), Bash(git status:*), Bash(git rev-parse:*), Bash(git diff-tree:*), Bash(git fetch:*), Bash(wc:*), Bash(grep:*), Bash(head:*), Bash(sed:*), Bash(python3:*), Bash(open:*), Bash(screencapture:*), Bash(gh:*), Bash(glab:*), Bash(GITLAB_HOST=*), Bash(codex:*), Bash(cursor:*), Bash(timeout*bob:*), Bash(bob:*)]
---

## Purpose

Catches bugs that tests and linters miss. Tests verify expected behavior,
linters check syntax — neither catches logic errors, security gaps, or
architectural problems that only a fresh-context reader spots.

## Arguments

$ARGUMENTS

## Context

- Current git status: !`git status --short 2>/dev/null || echo "Not a git repo"`
- Current branch: !`git branch --show-current 2>/dev/null || echo "N/A"`
- Recent commits: !`git log --oneline -5 2>/dev/null || echo "N/A"`
- Diff size: !`git diff --stat 2>/dev/null || echo "N/A"`
- Project conventions: !`head -30 CLAUDE.md 2>/dev/null || echo "No CLAUDE.md"`

## Ground Rules

These apply throughout. Internalize them before starting.

**What NOT to flag** — these create noise that drowns out real findings:
- Pre-existing issues (unless the change makes them worse) — the author didn't introduce them, so flagging them is unfair and distracting. Exception: audit mode, where the current state IS the subject.
- Intentional behavior clear from commit messages or context — the author chose this deliberately.
- Linter/compiler territory (formatting, unused imports, type errors) — automated tools catch these better than review.
- Style preferences without explicit project conventions — without a convention to cite, it's just opinion.
- Hypothetical issues without a concrete triggering scenario — if you can't construct the failure, it's speculation.
- Issues on unchanged lines when reviewing diffs — same as pre-existing; the author didn't touch them.
- "Best practice" suggestions that don't prevent a concrete problem — the reviewer's job is to catch bugs, not teach patterns.

**Precision over volume** — one confirmed finding with evidence beats ten speculative ones. When in doubt, downgrade severity. When still in doubt, drop the finding entirely.

**Confidence tags** — every finding gets one:
- `confirmed` — you traced the exact code path and constructed a triggering input
- `likely` — the code pattern is dangerous and no defense was found, but you couldn't construct a complete trigger
- `verify` — suspicious pattern but you lack context to confirm; flagged for the author's judgment
- `runtime-needed` (modifier, combinable with any above) — depends on runtime state that can't be verified from code alone. State what specific runtime check would confirm or disprove it

## Phase 0: Scope & Setup

### Determine Scope

| Input | Action |
|-------|--------|
| No arguments | Uncommitted changes (`git diff` + `git diff --cached`). If none, last commit. If not git, ask. |
| `staged` or `pre-commit` | Staged changes only (`git diff --cached`). If nothing staged, stop. |
| `last commit` | `git diff HEAD~1..HEAD` |
| `last N commits` | `git diff HEAD~N..HEAD` |
| File/directory path | Full review of that file or directory |
| Commit range (`abc..def`) | Diff between those commits |
| Natural language ("what I changed today") | Map to appropriate git commands |
| Full repo / "audit this repo" | **Audit mode** — see `references/report.md` § Audit Mode |
| MR/PR URL or `!N` / `#N` | **MR/PR review mode** — see `references/mr-review.md` |
| `--design` flag | **Design-review mode** — invoke brainstorming skill on the scope |
| `--re-review` or `--follow-up` | **Re-review mode** — see `references/re-review.md` |

**Scope gate (RENDERED before Phase 1):**
```
Scope: [type] - [file count] files, [line count] lines
Input implied: [what the input suggests] | Determined: [what you chose]
```
If the determined scope covers less than half the implied scope, confirm the reduction with the user before proceeding.

### Capability Detection

Read `config.md` (in this skill's directory) and determine the review tier.
If `config.md` is not readable or not configured, default to **Solo tier**
(Claude-only — all phases run, no cross-model agents):

```
Tier: [Solo / Dual / Full / Max]
Available: Claude=Y, Gemini=[Y/N], Codex=[Y/N], Cursor=[Y/N], Bob=[Y/N]
Agent budget: [3-4 / 6-8 / 10-12 / 12-21]
```

### Fast Path

For trivial changes (comment-only, version bumps, formatting, <20 code-relevant lines with no security-relevant files AND no functional behavior change), do a single-pass scan and report CLEAN. Skip all agents.

**RENDERED GATE (mandatory before fast-path):**
```
Fast-path check:
- Code-relevant lines: [N] (<20? YES/NO)
- Functional behavior change: [YES/NO - describe what changes]
- Security-relevant files: [YES/NO]
- Adds data sources/endpoints/config entries: [YES/NO]
- Verdict: [FAST-PATH (all criteria met) / FULL REVIEW (any criterion failed)]
```

Fast path EXCLUDES changes that add new data sources, repos, endpoints, or config entries — even at 1 line, these require tracing the consumer code path.

### Trivial Tier

For changes that FAIL fast-path but are still very small (<=10 code-relevant lines, <=5 files, no security-sensitive files): run Phase 1 + own analysis + 2 cross-model agents. Skip the full perspective sweep.

**RENDERED GATE:**
```
Trivial-tier check:
- Code-relevant lines: [N] (<=10? YES/NO)
- Files changed: [N] (<=5? YES/NO)
- Security-sensitive files: [YES/NO]
- Verdict: [TRIVIAL (all met) / FULL REVIEW]
```

Security-sensitive = auth, credentials, crypto, input validation, access control — regardless of file path.

### Launch Cross-Model Review (non-trivial only)

For non-trivial reviews, launch available cross-model agents in the **background** immediately — they run in parallel while you do Phases 1-3.

Read `references/cross-model.md` for dispatch instructions per tool. The general pattern:

- **Gemini**: call MCP tools directly (synchronous, results inline)
- **Codex**: `Bash(run_in_background: true)` with `codex exec -o $RESULT_FILE`
- **Cursor**: `Bash(run_in_background: true)` with `cursor agent --print -o $RESULT_FILE`
- **Bob**: `Bash(run_in_background: true)` with Python subprocess writing to result file
- **Claude agents**: foreground `Agent()` calls — dispatch multiple in ONE message for parallelism

**CRITICAL: Do NOT use `Agent(run_in_background: true)` or `Agent(name: "...")` for one-shot review agents.** Both patterns lose results. Use anonymous foreground `Agent()` calls dispatched in the same message for parallelism.

### Phase -1: Design Exploration (optional)

**Trigger**: explicit `--design` flag or user asks about the design approach.
Skip for: bugfixes, refactors, config changes, dependency updates, test/docs-only changes.
`--design` flag overrides the skip list.

Invoke `Skill(skill="superpowers:brainstorming")` if available. If unavailable, skip with a note. Phase -1 is always optional — a failed design exploration never prevents the review.

**Output**: design context block before Phase 1:
```
Design exploration:
- Approach chosen: [what the code implements]
- Alternatives: [2-3 approaches with trade-offs]
- Assessment: [SOUND / QUESTIONABLE / REVIEW-NEEDED]
- Review focus areas: [specific concerns]
```

If Phase -1 ran, include design context in ALL agent prompts.

---

## Phase 1: Understand

Before judging any code, understand it. Every step prevents a category of false positives.

**Always do:**

1. **Collect the diff AND full file context** — read the full file for each changed code file, not just diff hunks. Skip binary files, submodule pointers, and auto-generated files. For very large files (1000+ lines), read the changed functions and their callers. Before analyzing, note what the surrounding code GUARANTEES: what does it validate? What errors does it handle? What does it assume about inputs?

2. **Classify the change** — determines what to scrutinize:

   | Change Type | Primary Focus |
   |-------------|---------------|
   | New feature | Correctness, edge cases, API contract, missing validation |
   | Bug fix | Root cause vs symptom, regression risk, reproducibility |
   | Refactor | Behavioral equivalence — old and new must produce identical results |
   | Config/infra | Environment differences, rollback safety, secret exposure |
   | Dependency update | Breaking changes, security advisories, maintenance status |
   | Test changes | Assertion specificity, mock fidelity, flaky patterns |
   | DB migration | Reversibility, data loss risk, locking, idempotency |
   | Port/migration | Source equivalence, regression on existing consumers |

   **Port detection**: if the PR description mentions "migration"/"port" or new code has a same-named equivalent in a source repo, read the ENTIRE source before forming findings. Patterns matching the source are intentional ports — downgrade to Suggestion.

3. **Identify the tech stack and defenses** — note framework/library-provided protections (ORM parameterization, CSRF middleware, auth decorators). Don't flag issues they already handle. If the project has a CLAUDE.md, read the full file for coding conventions.

4. **Read surrounding code** — grep for imports and usages of changed functions. Know who calls it and what it returns. For template-based code (Ansible, Helm, Jinja2): resolve `{{ variable }}` references from defaults/vars files.

**For MR/PR reviews**: also execute the MR-specific Phase 1 steps from `references/mr-review.md` (consumer impact, operational regression, prior review verification, submission metadata, upstream docs).

**Do when applicable** (mandatory for MR/PR and large diffs):

5. **Understand intent** — read commit messages. For multi-commit scopes, read each individually.
6. **Check recent history** — `git log --oneline -10 [file]` on key files with complex logic or high churn.
7. **Detect diverged copies** — when you find structurally similar code blocks, diff them side-by-side.
8. **Check language-specific patterns** — read `references/patterns.md` for the relevant language.

### Phase 1 Completion Gate (blocks Phase 1.5)

**RENDERED GATE:**
```
Phase 1 complete:
- Full files read: [N files]
- Change classified: [type]
- Tech stack defenses: [list]
- Callers/consumers traced: [Y/N]
- Cross-model launched: [list agents or "Solo tier"]
```

---

## Phase 1.5: Logic & Approach Analysis

Before checking whether the code is CORRECT, check whether the APPROACH is SOUND. This phase exists because the most expensive review failures aren't missed bugs — they're reviews that verify the syntax of code that solves the wrong problem or references resources that don't exist. Catching approach issues early saves the entire Phase 2 analysis from being wasted effort.

**Agent dispatch** (adapted to tier):

| Tier | Agents |
|------|--------|
| Solo | 1 Claude approach analyst (foreground) |
| Dual | 1 Claude + 1 cross-model (Gemini or Codex) |
| Full+ | 4 agents across 3+ families (see `references/cross-model.md`) |

**After dispatching, analyze 7 dimensions yourself:**

1. **Goal alignment** — does the change solve what the commit message says? If not, what's the gap?
2. **Approach fitness** — is this the right way? Does the repo have existing patterns for this type of change? Would an existing pattern reduce complexity?
3. **Value correctness** — for each new literal value (IDs, ports, versions, hostnames): grep the repo for prior usage. Zero prior uses = NOVEL. Novel values need runtime verification.
4. **Dependency completeness** — for every file path or resource referencing another repo: verify it EXISTS. Three outcomes: exists on default branch (PASS), exists only in unmerged PR (Warning), doesn't exist (Critical).
5. **Scope appropriateness** — over-engineered, under-scoped, or just right?
6. **Assumption validity** — what does the code assume that may not be true at runtime? List each and tag `runtime-needed`.
7. **Integration soundness** — does the change fit with the rest of the system?

**RENDERED GATE (blocks Phase 2):**
```
Phase 1.5 - Logic & Approach:
- Goal alignment: [matches / MISMATCH: why]
- Approach fitness: [sound / ALTERNATIVE: existing pattern at <file:line>]
- Value correctness: [N novel values, each grep-verified]
- Dependency completeness: [all exist / N missing]
- Scope: [appropriate / OVER/UNDER-SCOPED]
- Assumptions: [N runtime assumptions, each tagged]
- Integration: [fits / CONFLICT]
Agents: [list dispatched and findings count]
```

---

## Phase 2: Analyze & Prove

Adapt focus to both **code type** and **change type** from Phase 1. If Phase 1.5 identified approach concerns, prioritize those in code analysis.

**Strategy by scope size:**
- **Small (1-3 files, <200 lines)**: Single-pass deep review
- **Medium (4-10 files, 200-500 lines)**: Triage by risk. Deep review high-risk files, scan low-risk
- **Large (10+ files or 500+ lines)**: MUST use parallel agents — read `references/agents.md`

**Multi-commit scopes**: review commit-by-commit first, then combined diff for cross-commit interactions.

### Analysis Dimensions

Read `references/checklist.md` and walk through each applicable dimension:
- Correctness & Logic
- Security (data-flow analysis)
- Error Handling & Resilience
- Performance
- API & Contract
- Dependencies (when in scope)
- Test Quality (when in scope)
- Codebase Alignment
- Container/Dockerfile Hardening (when in scope)
- Kubernetes/OpenShift Manifests (when in scope)
- MCP Server Security (when in scope)
- Visual & UX (when HTML/CSS in scope)

### For Each Potential Finding

Before adding a finding to your list:
1. **Construct a concrete trigger** — specific input, state, or sequence
2. **Check existing defenses** — framework, upstream validation, middleware?
3. **Sibling check** — grep the codebase for the same pattern. This catches a common false positive: flagging code that follows the project's own established conventions. The author followed the pattern, they didn't create the problem.
   `Sibling check: grep '<pattern>' <codebase> -> N hits | Convention? [YES -> DOWNGRADE | NO -> keep] | Security? [YES -> KEEP regardless]`
   If the pattern exists in 2+ sibling files AND is NOT a security issue, it's an established convention — downgrade or drop. Security issues that are widespread are WORSE, not better — flag as "systemic: N files affected."
4. **Cross-reference tests** — do existing tests cover this path?
5. **Cite exact `file:line`** — verify each citation with Read

If you cannot construct a trigger after reasonable effort, drop the finding.

### Severity Classification

| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Security breach, data loss, crash, or silent corruption in production | SQL injection, auth bypass, unhandled null on common input |
| **Warning** | Real issue under specific conditions, violates a clear contract | Race condition under load, missing cleanup on error, weak crypto |
| **Suggestion** | Improvement that isn't broken. No concrete failure in normal use | Perf optimization for non-hot path, better error message |

**Calibration:** Multiple preconditions = Warning, not Critical. Any malformed input to public API = Critical. Code with only Suggestions is CLEAN.

---

## Phase 2.5: Perspective Agents

Launch role-based perspective agents that review from **stakeholder viewpoints**, not code dimensions. Code agents check IF the code works. Role agents check HOW the product behaves for different stakeholders.

**Dispatch count by tier:**

| Tier | Code perspectives | Content perspectives (deliverables) |
|------|------------------|-------------------------------------|
| Solo | P3 (Senior Eng + Skeptic), P6 (Accessibility) | C1-C3 (Claude-only) |
| Dual | + P1 (UX via Gemini or Claude) | + C4-C6 |
| Full | + P2 (QE), P4 (Platform), P5 (Architecture) | + C7-C8 |
| Max | All P1-P7 (12 agents, 5 families) | All C1-C9 (9 agents) |

Read `references/perspectives.md` for full prompt templates and dispatch rules per tier.

**Key dispatch rules:**
- Claude perspectives: FOREGROUND anonymous `Agent()` — dispatch multiple in ONE message for parallelism
- Gemini: direct MCP calls (synchronous)
- Codex/Bob/Cursor: `Bash(run_in_background: true)` writing to result files
- Content perspectives (C1-C9): ONLY for deliverables (presentations, reports, proposals, READMEs >500 words)

**DISPATCH LEDGER (RENDERED before dispatching):**
```
| # | Agent | Model | Dispatched? |
|---|-------|-------|-------------|
| P3a | Senior Eng | Claude | _fill_ |
| P3b | Skeptic | Claude | _fill_ |
| P6 | Accessibility | Claude | _fill_ |
| ... | ... | ... | ... |
| **Total** | | | **_/N** |
```
Any ALWAYS row with blank Dispatched? -> STOP and dispatch.

---

## Phase 3: Verify & Filter

**Switch to adversarial mode.** Your goal is now to DISPROVE each finding. This mental shift matters because the analysis phase creates confirmation bias — once you've identified a pattern as a "bug," your brain (or weights) resist reclassifying it. The antidote is to actively seek reasons each finding is wrong. A finding that survives genuine disproof attempts is trustworthy; one that only survived because you didn't try to disprove it is noise.

For each finding:

1. **Try to disprove it:**
   - Does the framework/library already handle this?
   - Is there input validation upstream?
   - Does git history show this is intentional?
   - Do existing tests assert this behavior?
   - Can the preconditions actually co-occur?
   If you find a defense, downgrade or drop.

2. **Self-audit checklist:**
   - [ ] Concrete triggering scenario exists
   - [ ] Evidence from actual code, not assumed
   - [ ] A senior developer on this project would agree
   - [ ] About the changed code, not pre-existing
   - [ ] Severity calibrated correctly
   - [ ] Would fixing this prevent a real incident?
   - [ ] Hot path or dead code?
   - [ ] Tried to disprove and failed
   - [ ] Every `file:line` verified with `sed -n 'Np'`
   - [ ] Not something a linter/type checker catches
   - [ ] Not silenced by an explicit ignore annotation

   Cut anything that fails any checkbox.

3. **Verification agent** — for every Critical finding, dispatch a verification subagent (see `references/agents.md` § Verification Agent). For Warnings below `confirmed`, also verify. The reviewer who generated a finding has confirmation bias a fresh agent doesn't.

4. **Final confidence gate** — any finding still `verify` after self-audit AND verification -> drop. Only `confirmed` and `likely` survive.

### Phase 3.5: Quality Gate

Before writing the report, verify each applicable item:
- [ ] Every `file:line` reference verified with `sed -n 'Np'`
- [ ] Blast radius checked for changed functions/variables
- [ ] Hardcoded values verified against existing variables/configs
- [ ] New code compared against similar code in the repo

**Self-confidence gate (RENDERED):**
```
Confidence self-check:
- What I'm NOT confident about: [list - empty = suspect]
- What I didn't verify: [list]
- What would the AUTHOR say is wrong: [prediction]
```
If gaps exist, INVESTIGATE immediately — don't present them as questions.

### Phase 3.7: Merge Cross-Model Findings

**RENDERED before merging:**
```
Independent review complete:
- Phase 0 agents: [list launched / "Solo tier"]
- Dimensions checked: [list from checklist.md]
- Own findings: [count] (list titles)
- Phase 3.5 gate: [PASS / items marked N/A]
- Perspectives: [P1=result ... P7=result, per tier]
- Models: [families with agent counts]
```

Collect results from each cross-model agent. For each:
- **Found something you missed** -> investigate from source. If valid, add with `[cross-model]` tag
- **You found something they missed** -> keep yours
- **Both found same issue** -> `confirmed` (high confidence)
- **False positive** -> drop

**Contradiction detection**: when 2+ models reach opposite verdicts on the same location, investigate from source independently. Resolution becomes a `confirmed` finding.

### Phase 3.9: Final Quality Gate

```
Final finding list ([count] total):
1. [severity] title (source: Claude|Gemini|Codex|...) - file:line verified? Y/N
...
Duplicates removed: [count]
Contradictions resolved: [count]
```

**Teammate approval test (MR/PR reviews):**
- 0 Warnings/Criticals AND Suggestions < 5 -> APPROVE + list optional improvements
- 0 Warnings/Criticals BUT Suggestions >= 5 -> REVIEW (aggregate concern)
- Any Warning/Critical -> BLOCK or REVIEW per severity

**Findings cap**: 10 for diffs, 20 for MR/PR reviews and audits.

---

## Phase 4: Report

Read `references/report.md` for the full template, verdict criteria, and formatting.

**Key rules:**
- **Verdict**: BLOCK (confirmed Critical), REVIEW (Warnings), CLEAN (Suggestions only)
- Lead with verdict + metrics table, evidence second
- Every `file:line` verified. Every reference is a hyperlink (MR/PR mode)
- After report (non-MR): "Want me to fix any of these? (specify numbers, or 'all')"

### Phase 4.5: Auto-Draft Review (MR/PR only)

For MR/PR reviews, read `references/mr-review.md` § Phase 4.5 for auto-draft mechanics:
- Default to INLINE comments (one per finding, on the specific diff line)
- Max 2-3 sentences each, suggestive tone
- Create as PENDING review (not published)
- Verify patchset freshness before posting

### Phase 5: Feedback Capture

After presenting the report, if the user acts on findings:
- Track accepted, rejected (why?), and missed findings
- Rejected as false positive -> severity was wrong
- Missed by review -> add pattern to `references/examples.md`

---

## Gotchas

- **Concept-level overlap != mechanism-level verification** — "we have a review tool" doesn't mean another model adds nothing. Compare at mechanism level.
- **Pre-existing issues vs changed code** — findings about code before the diff are noise. Exception: security findings in code the diff interacts with.
- **Self-review of own changes is confirmation bias** — when reviewing code YOU wrote, dispatch a fresh-context agent.
- **GitHub PRs may return `diff_lines=0` from some MCP tools** — always fetch the actual diff with `gh pr diff`.

## Calibration

Read `references/examples.md` when uncertain about severity or whether to flag something.
