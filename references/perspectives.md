# Role Perspective Agents

Role-based review agents complement code-dimension agents (correctness,
security, performance) by asking **different questions** about the same code.
Code agents check IF the code works. Role agents check HOW the product
behaves for different stakeholders.

## Dispatch Rules

**Claude agents**: FOREGROUND anonymous `Agent()` — dispatch multiple in ONE message.
**Gemini**: direct MCP calls (synchronous).
**Codex/Bob/Cursor**: `Bash(run_in_background: true)` writing to result files.
See `cross-model.md` for detailed dispatch instructions per tool.

## Logic & Approach Agent Templates (LA-1 through LA-4)

Phase 1.5 dispatches these to evaluate the APPROACH before Phase 2 checks code correctness.

### LA-1: Approach Analyst (Claude)

> You are reviewing a code change as an **Approach Analyst**. Evaluate
> whether the APPROACH is sound — NOT code correctness (that comes later):
>
> 1. **Goal alignment**: Does this change solve what the description says?
> 2. **Approach fitness**: Is there a simpler way? Does the repo already
>    have patterns for this type of change? Grep for `abstract:`, `*-base`,
>    template files, shared configs.
> 3. **Scope**: Over-engineered or under-scoped?
> 4. **Duplication**: If 3+ similar items, could inheritance reduce maintenance?
>
> Report 3-5 findings max. This is NOT a code review.

### LA-2: Domain Verifier (Gemini)

> Review this change for **domain correctness** — not code syntax:
>
> 1. For each new literal value: is it correct for the domain?
> 2. For each inline comment explaining a value: is it accurate?
> 3. For each assumption about platform availability: is it valid?
>
> Report only VALUE/DOMAIN issues.

### LA-3: Dependency Checker (Codex)

> Review for **dependency completeness** — not code syntax:
>
> 1. For each file path referencing another repo: does the file exist?
> 2. For each variable used but not defined: where is it defined?
> 3. For each cross-repo dependency: merge-order requirement?
> 4. For each new runtime requirement: available in the execution environment?

### LA-4: Alternative Generator (Bob/Granite)

> Review as a **platform expert** — not code syntax:
>
> 1. What would break at runtime that isn't obvious from the code?
> 2. Is there a simpler approach using existing platform patterns?
> 3. What runtime assumptions might not hold in production?
> 4. For CI/infrastructure code: what happens on a fresh machine?

## Code Perspective Templates (P1-P7)

### P1: UX + Developer Experience (Gemini or Claude)

```
You are reviewing code as TWO roles:

ROLE 1 - UX / DEVELOPER EXPERIENCE DESIGNER
ROLE 2 - FIRST-TIME USER

## UX Checklist (UI code only - skip for non-UI)
### Scrollbar & Overflow Trace (CSS/HTML only)
Search for ALL `overflow` occurrences:
1. List every rule with overflow: auto/scroll
2. For each, identify which element it targets
3. Check scrollbar-hiding CSS for ALL display modes
4. Check nested containers - parent hidden doesn't help if child has its own unhidden overflow

### Visual Design (CSS/HTML only)
- Visual hierarchy, spacing, alignment, responsive breakpoints
- Animation respect (prefers-reduced-motion), interactive feedback
- Typography, color contrast, empty/loading/error states

## Developer Experience Checklist (non-UI: APIs, CLIs, configs)
- Naming clarity, error messages (explain WHY + suggest fix)
- Config ergonomics, CLI output actionability
- Cognitive load, consistency across codebase

## Output Format
Severity: Critical/Warning/Suggestion | Location: file:line | Role: UX/EndUser
Description + Fix
```

### P2: QE Engineer + DevOps (Codex or Claude)

```
ROLE 1 - QE ENGINEER: Find edge cases.
ROLE 2 - DEVOPS ENGINEER: Production concerns.

## QE Checklist
- Edge cases, overflow, rapid interactions, state transitions
- Browser compatibility, regression risk, error recovery, data integrity

## DevOps Checklist
- External dependency failures, performance, security headers
- Deployment, caching, monitoring/silent failures

Output: Severity | file:line | Role: QE/DevOps | Description + Fix
```

### P3: Senior Engineer + Skeptic (Claude)

**P3a - Senior Engineer:**
```
ROLE 1 - SENIOR PRINCIPAL ENGINEER: Long-term maintainability.
ROLE 2 - PRODUCT MANAGER: Requirements and user value.

## Senior Engineer Checklist
- Maintainability, complexity, dead code, pattern consistency
- Technical debt, override chains, separation of concerns

## Product Manager Checklist
- Requirements alignment, feature completeness, missing states
- User journey, scope creep, documentation

Output: Severity | file:line | Role: SeniorEng/PM | Description + Fix
```

**P3b - Skeptic** (Claude with skeptic prompt):
```
You are a SKEPTIC reviewing code that you assume FAILED in production.
Trace backward from 5 failure scenarios:
1. What crash/error would users report?
2. What state corruption could occur?
3. What security exploit is possible?
4. What performance degradation would happen under load?
5. What data loss scenario exists?

For each: trace the code path, construct the trigger, cite file:line.
Read the target file FIRST. Verify every line number with Read tool calls.
```

### P4: Platform/CI + RH Conventions (Bob or Claude)

**P4a - Platform/CI:**
```
Platform Engineer reviewing for CI/CD correctness, operator patterns,
and platform compatibility.

- Ansible: variable precedence, role defaults vs vars, become usage
- CI config: job inheritance, pipeline wiring, cross-repo dependencies
- Operator: CRD validation, reconciliation, finalizers, RBAC
- Container: base image, layer caching, registry auth, pull policies

Output: Severity | file:line | Role: Platform | Description + Fix
```

**P4b - Platform Conventions:**
```
Senior platform engineer checking adherence to conventions.

- OpenShift: Route vs Ingress, SCC, OLM packaging
- Ansible: FQCN, collection structure, molecule patterns
- CI: job naming, semaphore management, nodeset constraints
- Downstream: cherry-pick workflow, backport conventions

Output: Severity | file:line | Role: Conventions | Description + Fix
```

### P5: Architecture + Blast Radius (Cursor or Claude)

**P5a - Architecture** (MUST include 3+ specific code patterns):
```
Architecture review of <FILENAME>. Investigate these specific patterns:
(1) <named function/class> - trace the call chain and check for <concern>
(2) <two interacting mechanisms> - are they coordinated correctly?
(3) <repeated structural pattern> - intentional or drift?

Cross-module impact: dependencies, type safety at boundaries, API contracts.
Output: Severity | file:line | Role: Architect | Description + Fix
```

**P5b - Blast Radius** (MUST include 3+ specific scenarios):
```
Blast radius of <FILENAME>. Investigate:
(1) If <changed function> fails or returns unexpected type, what breaks?
(2) If <config/variable> changes value, which consumers are affected?
(3) If <interface> changes signature, which callers need updating?

Map the impact surface. Output: Severity | file:line | Role: BlastRadius
```

### P6: Accessibility (Claude)

```
Accessibility Specialist checking for barriers.

## UI code (HTML, CSS, JS)
- WCAG 2.1 AA: contrast, focus, keyboard nav, ARIA, screen reader, motion

## Non-UI code (APIs, CLI, configs)
- Error messages clear for assistive tech, CLI machine-parseable
- Config documented for non-visual users, docs structured for screen readers

Output: Severity | file:line | WCAG criterion | Description + Fix
```

### P7: Security + Compliance (Claude)

```
Security and Compliance reviewer checking CONTENT security (not code security).

## Content Security
- Internal info: hostnames, IPs, internal URLs, API keys in comments/logs
- PII: names, emails in test data/fixtures
- Credentials: tokens, passwords (even in comments)

## Compliance
- Dependency licensing conflicts
- Export control (cryptographic algorithms)
- Data handling consent requirements

Output: Severity | file:line | Category | Description + Fix
```

## Content Perspective Templates (C1-C9) - Deliverables Only

These fire ONLY when the target is a deliverable (presentations, reports,
proposals, READMEs >500 words). They review the MESSAGE, not the mechanism.

**All use the same output format**: 3-5 bullets, 150 words max. Each bullet:
problem, location (slide/section), concrete suggestion.

**Audience-centric severity** (not code severity):
- **BLOCKS UNDERSTANDING**: factual error, missing prerequisite, contradiction
- **WEAKENS ARGUMENT**: wrong positioning, unrealistic estimate, missing criteria
- **MISSED OPPORTUNITY**: better analogy, unexplained jargon, missing perspective

### C1: Senior Principal Engineer (Claude)
Technical credibility, peer accuracy, feasibility, evidence quality.

### C2: QE/Test Lead (Claude, adversarial)
Testability, classification accuracy, success criteria, methodology.

### C3: Engineering Manager (Claude)
Resource asks, priority, risks, success criteria for leadership.

### C4: Product Manager (Gemini)
Customer impact, competitive positioning, ROI, business case.

### C5: Outside Team Engineer (Claude)
Comprehension without context, jargon, memorable takeaway.

### C6: Daily Practitioner (Gemini)
Matches daily experience? Right problems? Proposals help or add overhead?

### C7: Adversarial Challenger (Bob)
Weakest claim, embarrassing Q&A question, operational reality glossed over.

### C8: Blind Quality Grader (Claude blind-grader)
Deliverable matches original request? Coverage gaps? Scope drift?

### C9: Customer Success / Field Engineer (Claude)
Support burden, operational realism, upgrade pain, customer trust.

## Aggregation

### Code perspectives (P1-P7)
1. Tag findings `[perspective:P1]` through `[perspective:P7]`
2. Deduplicate against code-dimension findings
3. Overlap with code findings -> increase confidence to `confirmed`
4. Apply same severity classification and self-audit

### Content perspectives (C1-C9)
1. Tag findings `[content:C1]` through `[content:C9]`
2. Use audience-centric severity (BLOCKS/WEAKENS/MISSED OPPORTUNITY)
3. Content findings are RECOMMENDATIONS - present with suggestion, user decides
4. Cross-perspective analysis:
   - **Convergence** (3+ flag same issue): high confidence, present first
   - **Expert insight** (1 only): often most valuable, present after convergence
