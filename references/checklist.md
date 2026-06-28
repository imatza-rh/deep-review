# Analysis Checklist

> **Contents**: Correctness & Logic — Security (data-flow) — Error Handling — Performance — API & Contract — Dependencies — Test Quality — Codebase Alignment — Semantic Value — Container/Dockerfile — K8s/OpenShift — MCP Server — LLM Steganography — Agentic/Multi-Agent — AI Config Supply Chain — GitHub Actions/CI — Go Security — Visual & UX

Walk through each applicable dimension for the changed code. Skip dimensions that don't apply (e.g., Dependencies for non-dependency changes, Test Quality when no test code changed). For findings that depend on runtime state you can't verify from code (e.g., what a DHCP server pushes, load balancer routing, service mesh config), add `runtime-needed` to the confidence tag and state what check would confirm or disprove it.

## Correctness & Logic
- Trace all code paths including edge cases and boundary conditions
- Off-by-one, null/undefined, empty collection, zero-value, integer overflow/truncation
- Race conditions and concurrency (mutex ordering, atomicity gaps, shared state under load)
- State machine transitions — are all valid states and transitions handled?
- Does the code actually implement the stated intent?
- **Author-pattern comparison**: compare how the author handles the SAME concern in different parts of this change. If the author restricts binding on one socket but uses `0.0.0.0` on another, or validates input in one handler but not a sibling, the inconsistency is a finding the author will agree with — their own code proves they know the better pattern.
- **Three adversary test** (only for changes that define APIs, configs, defaults, or public interfaces — skip for internal logic, bug fixes, and refactors): beyond the security attacker, consider the **lazy developer** (copies the first example they find — is the easy/default path secure?) and the **confused developer** (misreads the API, swaps parameters, uses wrong enum — does the code fail safely or silently corrupt?). If the default behavior is insecure or parameter swap compiles without error, flag it.
- **Code comment compliance & rot**: check if the change violates directives in existing code comments (`TODO`, `FIXME`, `IMPORTANT`, `NOTE`, `HACK`, `WARN`, `XXX`). If a comment says "always call cleanup() after this" and the PR adds a new caller that doesn't, that's a `confirmed` bug. Also check the reverse: does the change make existing comments INACCURATE? A function comment saying "returns sorted list" when the sort was removed is comment rot — worse than no comment. Grep changed files for comments in the same function/block as changed lines and verify each still matches the code.
- **Absolute language vs counter-examples**: grep changed documentation files for absolute claims (`Never`, `Always`, `Must`, `Every`, `No exception`). For EACH match: verify against the codebase with a targeted grep. If a counter-example exists in code (the code does the thing the doc says "never" to do), flag as incorrect absolute claim. A doc saying "Never use HasPrefix for security matching" with `strings.HasPrefix` in the actual security code is a `confirmed` inconsistency — either the doc or the code is wrong.

## Security (data-flow analysis)
- Trace external inputs from entry through all transformations to sinks (taint analysis)
- For every potential security finding, write the explicit data-flow path: `user_input → func_A:12 → func_B:45 → sql_query:67`. If you cannot trace a complete path, the finding is invalid.
- Injection: SQL, command, path traversal, XSS, template injection, SSRF
- Auth: are access controls checked before sensitive operations? Can they be bypassed? IDOR?
- Secrets: credentials, tokens, or keys in code, logs, error messages, or comments?
- Deserialization: pickle, yaml.load, JSON parser abuse, XML external entities
- Timing: constant-time comparison for auth tokens and secrets?
- **Exploitability assessment** (for each security finding): model the attacker — what access is needed? (web: anonymous/authenticated/admin; CLI: malicious input file/env var; MCP: prompt injection; library: malicious caller; CI: PR submitter). Write the concrete exploit — not "could be exploited" but HOW. Rate: **trivial** (single request/input), **moderate** (specific conditions needed), **difficult** (insider + chained vulns). Use this to calibrate severity — a "Critical" needing admin + local + timing is really a Warning.
- **Attack surface priority** (guides WHICH security issues to look for first): auth/permissions/tenant isolation > data loss/corruption/irreversible state > rollback/retry/idempotency gaps > race conditions/stale state > empty-state/null/timeout > version skew/schema drift > observability gaps.

## Error Handling & Resilience
- What happens when a dependency errors, times out, or returns unexpected data?
- Resource cleanup on failure — file handles, connections, locks, temp files
- Silent error swallowing (bare `except: pass`, empty catch blocks)
- Retry storms and cascading failures — can retries amplify an outage?
- **Silent failure hunt** — for each error handler: (1) Would this log help debug the issue 6 months from now? (2) List unexpected exception types a broad `except Exception` could swallow. (3) Should this error bubble up instead? (4) Does the fallback mask the real problem? (5) Check for: empty catch blocks, catch-log-continue, returning None on error without logging, retry exhaustion without notification.

## Performance
- Algorithmic complexity — O(n²) or worse in hot paths?
- N+1 queries, redundant I/O, unbounded collections, missing pagination
- Resource leaks — connections, timers, event listeners not cleaned up
- For long-running services: shared state, connection pool exhaustion, concurrent memory multiplication

## API & Contract
- Does the change honor its interface contract (types, return values, side effects)?
- Backward compatibility — does the change require callers to update?
- Blast radius — grep for all usages of changed functions/variables/configs. For each direct caller, grep for ITS callers too (2-level trace). For config/variable changes: grep the codebase for all consumers of the value. Report in the `## Verified` section: "Blast radius: N direct + M transitive callers — `file_a.py:30` → `file_b.py:55`"
- Semantic impact (for heterogeneous repos with YAML/config/docs alongside code) — structural blast radius (grep/callers) misses non-code relationships. For each changed file: (1) classify its category (code/config/docs/infra/data/script/markup), (2) expand 1-hop via category-appropriate references (config: what reads this YAML key; infra: what depends on this Dockerfile; docs: what references this section), (3) list affected business capabilities. This catches impact chains that structural BFS misses — e.g., a YAML variable rename affecting 5 Ansible roles that grep for the old name, or a Dockerfile base image change affecting all services built from it. Report as: "Semantic impact: N files across M categories — [config: what changed] → [code: N consumers] → [capability: what breaks]."
- New-caller side effects — when new code calls an existing function, check whether ALL of the called function's behaviors (not just the one you care about) are appropriate for the new calling context. A function designed for context A (search text changes → preserve table selection) may have wrong side effects in context B (folder switch → should reset selection). Read the full body of each called function, list every side effect, verify each one.

## Dependencies (when dependency changes are in scope)
- Is the new dependency justified? Could the functionality be achieved without it?
- Check maintenance status — actively maintained? Last release? Known security advisories?
- License compatibility — does the new license conflict with the project's license?

## Test Quality (when test code is in scope)
- Assertion specificity — testing behavior, not implementation details?
- Test isolation — no shared mutable state between tests?
- Determinism — no time-dependent, network-dependent, or order-dependent tests?
- Mock fidelity — do mocks match the real interface?

## Codebase Alignment (for new features and config changes)
- For each hardcoded value in new code, check if a variable already exists for that value in group_vars, defaults, or vars files. Hardcoding a value that has a variable is a WARNING.
- For each hardcoded value used as a match pattern (regex, sed, grep), cross-reference against the codebase's own configuration to verify the pattern actually matches. **Check ALL variables that could produce matching values** — grep the entire config file for the pattern's literal prefix. A match pattern can be reached through multiple variable paths. A sed pattern that doesn't match ANY path in the codebase's own config is a CRITICAL (dead code or silent failure). A pattern that matches SOME paths but not the obvious one is a QUESTION for the author.
- Compare new code against existing code that does the same thing. Note deviations — intentional improvements or missed patterns?
- For new features: check if upstream documentation exists. If no upstream docs, note it (WARNING for internal tools, CRITICAL for production-facing).
- **Workaround detection**: for patterns that bypass normal mechanisms (SSH into managed nodes, TCP proxies, manual sed on operator-managed configs, ip6tables DNAT, background HTTP servers), flag as workaround. Check if upstream fix exists and when it merged (`gh pr view N --repo org/repo --json mergedAt`). If upstream fix is shipped in the target version, the workaround should document why it's still needed and add version guards.
- **Approach soundness** (for MRs adding 3+ structurally similar items): when the diff adds 3+ items that share >80% identical structure (job definitions, config blocks, resource manifests), check: (a) Does the repo have an existing inheritance/template/abstract pattern for this type? (grep for `abstract:`, `*-base` naming, template files, shared defaults). (b) Would an abstract base + concrete overrides reduce duplication WITHOUT adding complexity? (c) Are the differences between items INTENTIONAL and DOCUMENTED? (different OS versions = intentional; copy-paste with forgotten edits = bug). Flag as Suggestion if an existing pattern would reduce duplication. Not blocking - duplication is sometimes correct for small sets.

## Semantic Value Analysis (reference patterns — execution happens in Phase 1.5, NOT during Phase 2 checklist walk)
- **Novel value detection**: for each new literal value in the diff — whether inline or in vars/defaults files — (numeric IDs, ports, version strings, hostnames), grep the ENTIRE repo for prior usage. Zero prior uses = NOVEL. Novel values have never been validated in this codebase - flag as `verify, runtime-needed` with the specific runtime check needed (e.g., "verify operatingsystem_id 86 exists in Foreman"). The existing repo's value set (which IDs ARE used) is the baseline for detecting novelty.
- **Comment-claim verification**: inline comments explaining a value (e.g., `#RHEL9.6`, `#port for X`) are CLAIMS, not evidence. For novel values with explanatory comments, search for a cross-reference source (sibling file with the same ID, external docs, API). If no source is accessible, tag `verify, runtime-needed` and state what check would confirm it. The comment might be wrong - the reviewer who added it during a prior review round also didn't verify.
- **Cross-repo file existence**: for every file path referencing another repo (testconfigs, playbooks, variable files, scripts), verify the file EXISTS on that repo's default branch: local clone (`ls`/`find`), GitHub (`gh api repos/.../contents/...`), or GitLab (`glab api`). Three outcomes: (a) exists on default branch → PASS, (b) exists only in an unmerged PR → **Warning**: "Merge-order dependency: [file] exists only in [PR URL] (state: OPEN). Jobs/code referencing this file will fail until that PR merges," (c) does not exist anywhere → **Critical**: "Referenced file [path] does not exist in [repo] - guaranteed runtime failure."
- **Functional delta analysis**: when new config references a variant of an existing resource (e.g., `osp_verification_4.21_nightly.yaml` vs `osp_verification.yaml`), diff the variant against the original. Report: "Stages changed: [added/removed]. New parameters: [list]. Removed capabilities: [list]." Each difference is a Question for the author - not a bug, but must be intentional. A stage removed silently (e.g., `cpms_test` replaced by `day2ops`) changes what the job validates.

## Container/Dockerfile Hardening (when Dockerfile or Containerfile is in scope)
- Base image: minimal or distroless (e.g., UBI minimal, distroless, Alpine)
- Red Hat images: floating tags (Red Hat manages updates); non-RH images: pin by digest
- Multi-stage builds; no build tools in final image
- USER non-root; never run as root
- COPY specific files, not entire context
- No secrets in ENV, ARG, or COPY
- Read-only rootfs where possible
- No package manager cache in final layer
- HEALTHCHECK defined (standalone Docker; skip for containers that run inside K8s pods where probes handle health)

## Kubernetes/OpenShift Manifests (when YAML manifests, Helm templates, or operator configs are in scope)
- securityContext: runAsNonRoot, readOnlyRootFilesystem, allowPrivilegeEscalation: false
- Drop ALL capabilities, add only what is required
- Resource limits (cpu, memory) on every container
- No hostPID, hostNetwork, hostIPC, privileged: true
- NetworkPolicy defined for the namespace
- OpenShift: SCC must be restricted or custom-scoped
- Liveness + readiness probes defined
- automountServiceAccountToken: false unless needed
- RBAC: least privilege; no cluster-admin for workloads
- Helm: no .Values interpolation in shell commands

## MCP Server Security (when MCP server code is in scope)
- Sanitize all tool inputs against declared schemas
- Reject path traversal in file-accessing tools
- No credential forwarding to downstream services
- Tool injection: validate registry integrity, reject dynamic tool loading from untrusted sources
- Audit log all tool invocations with caller identity
- Rate limiting per client/scope

## LLM Output Steganography (when AI-generated text is in scope — commit messages, PR descriptions, code comments, log output, generated configs)
- LLM output can carry hidden messages via probability-rank selection (Calgacus protocol, ICLR 2026). The stegotext is statistically indistinguishable from normal output — pattern-matching tools (gitleaks, regex, OWASP scanners) CANNOT detect it.
- Threat model: data exfiltration (NOT prompt injection). A compromised dependency could use any text field as a covert channel.
- CI environments are especially vulnerable: pinned Docker images, GPU runner tags, and declarative job configs satisfy the hardware-determinism constraint Calgacus requires — by design.
- No detection mechanism exists for this class of attack. Awareness-only: flag AI-generated text in security-sensitive output paths.
- Related: tokenizer tampering (HiddenLayer) — modified tokenizer.json can change model outputs without altering weights., @arewm #forum-pnd-ai-community data exfiltration framing)

## Agentic / Multi-Agent Security (when agent systems, MCP clients, or multi-agent workflows are in scope)
- Agent identity: agents MUST have own identity, not impersonate human users (audit trail, blast radius)
- Agent-to-agent auth: SPIFFE/SPIRE + mTLS for inter-agent communication; no shared secrets over network
- Tool/server injection (rug-pull): sign MCP server updates with Sigstore/cosign; pin versions; verify integrity before auto-update
- Prompt injection mitigation: layered defense (runtime guardrails, model safety benchmarks, input/output filtering); no single control is sufficient
- Agentic actions auditor: check CI workflows for attacker-controlled input reaching AI agent prompts (env var intermediary, expression injection, wildcard user allowlists)
- MCP client auth: validate OAuth2 protected resource metadata; verify dynamic client registration; check client metadata support

## AI Config Supply Chain (when .claude/, .cursor/, .vscode/, or agent config files are in scope)
- `.claude/settings.json` with `command` key in hooks: confirmed Miasma malware IOC. ANY hook that runs curl, wget, node, python, bash, eval, or pipes to sh is CRITICAL
- `.claude/settings.json` permission escalation: adding `allow` rules that override user-level `ask` — enables the agent to run arbitrary commands without approval
- MCP server additions: new `mcpServers` entries pointing to unknown URLs or running unknown binaries — potential C2 channel
- Diff-collapsed config files: GitHub collapses files >300 lines. Check if `.claude/settings.json` changes are hidden in a collapsed diff section alongside legitimate changes
- Agent config in PRs against repos that DON'T normally have `.claude/`: any PR adding `.claude/` to a repo that never had it is suspicious — verify with repo owner
- CLAUDE.md instruction injection: new CLAUDE.md content that instructs the agent to execute commands, modify files outside the project, or exfiltrate data
- Cross-reference: if the PR modifies BOTH code AND `.claude/` config, verify the config changes are necessary for the code changes. Unrelated config additions alongside code = high suspicion. See also: ai-guardian project.)

## GitHub Actions / CI Pipeline Security (when .github/workflows or CI configs are in scope)
- Pin actions by full SHA, not tag
- No secrets in logs; mask sensitive outputs
- Least privilege: minimize GITHUB_TOKEN permissions
- No pull_request_target with checkout of PR head
- Agentic CI actions: audit for prompt injection via issue/PR title/body flowing into LLM prompts
- Sign artifacts with Sigstore/cosign

## Go Security (when Go code is in scope)
- Never ignore error returns
- database/sql with placeholders; no fmt.Sprintf in queries
- Use stdlib crypto/* and golang.org/x/crypto; avoid third-party crypto libraries
- Integer overflow: bounds-check user-supplied sizes
- context.Context for cancellation and timeouts

## Visual & UX (when HTML, CSS, JSX/TSX, Vue, Svelte, or presentation files are in scope)

### Scrollbar & Overflow Audit (MANDATORY — grep-driven)
Run `grep -n 'overflow' <file>` and for EACH match:
1. Identify the CSS selector (which element gets this overflow property)
2. Check if the element has a fixed-height parent or constrained container
3. For `overflow: auto` or `overflow-x: auto`: does this create a visible scrollbar?
4. For EACH display mode (presenter, mobile, print): is the scrollbar hidden when unwanted?
5. Check ALL children that also have `overflow` — nested scrollbars are the #1 missed visual bug
6. For presentation/slide files: trace EVERY scrollable container (`.slide`, `.table-wrap`,
   `.expandable-body`, `.search-results`, custom containers) and verify scrollbar hiding in
   presenter mode. Missing ONE container = visible scrollbar on that slide.

### Layout & Spacing
- Content fit: does content fit within its container at the designed resolution? Check fixed-height containers.
- Responsive breakpoints: test at each `@media` breakpoint — do elements overlap, wrap awkwardly, or disappear?
- Mode switching: theme toggle, presenter mode, fullscreen — any visual glitches on transition?
- Touch targets: interactive elements must be at least 44x44px on mobile (WCAG 2.5.8)

### Animation & Motion
- Animation respect: `prefers-reduced-motion` must disable ALL animations (CSS keyframes AND SVG SMIL)
- Animation references: grep for `animation:` in CSS and inline styles. For EACH animation name,
  verify a matching `@keyframes` definition exists. Missing keyframes = silent animation failure.

### Accessibility & Contrast
- Color contrast: text-on-background ratios must meet WCAG AA (4.5:1 normal text, 3:1 large text)
- Focus indicators: all interactive elements must have visible `:focus-visible` styles

### Search & Filter Transparency
When reviewing search/filter/sort code:
- **Match visibility**: if a search matches on field X, is field X visible in the result display? Truncated lists (showing 3 of 5 tags), hidden fields (body text, metadata), and filtered displays can make results appear unexplained to the user. The matching field must be visible or the match source indicated.
- **Mode indicators**: when multiple search modes exist (prefix toggle, mode switch), is the current mode visually clear? Can the user tell WHY results changed?
- **Sort stability**: does changing the search query reset sort/filter state? Stale sort modes from a previous query applied to new results produce confusing order.


### Dead Code Detection
- Dead CSS: selectors targeting classes that don't exist in the HTML (grep class names in CSS vs HTML)
- Dead keyframes: `@keyframes` definitions not referenced by any `animation:` property
