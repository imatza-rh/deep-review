# deep-review

A Claude Code skill for deep code review with multi-model verification.

Catches bugs that tests and linters miss — logic errors, security gaps,
architectural problems, and approach issues that only a fresh-context
reader spots.

## What it does

- **7-phase review methodology** — scope detection, understanding, approach analysis,
  deep analysis, multi-perspective review, verification/filtering, structured reporting
- **Adaptive multi-model dispatch** — works with Claude alone, scales up automatically
  as you add Gemini, Codex, Cursor, or Bob Shell
- **21 analysis dimensions** — correctness, security (data-flow tracing), error handling,
  performance, API contracts, container hardening, K8s/OCP manifests, MCP server security,
  CI pipeline security, visual/UX, and more
- **Up to 21 perspective agents** — reviews from UX designer, QE engineer, senior architect,
  skeptic, accessibility specialist, security reviewer, and 9 content perspectives for
  deliverables (presentations, reports, proposals)
- **MR/PR review mode** — fetches metadata, checks submission quality, auto-drafts inline
  comments as pending review, handles re-review follow-ups
- **Calibrated severity** — concrete triggers required for every finding, sibling-check
  to avoid flagging established patterns, verification agents to disprove findings

## Quick Start

1. Copy the skill into your Claude Code skills directory:
   ```bash
   cp -r deep-review ~/.claude/skills/
   ```

2. Edit `config.md` to declare your available tools:
   ```yaml
   claude: true    # always
   gemini: false   # set true if you have Gemini MCP
   codex: false    # set true if you have Codex CLI
   cursor: false   # set true if you have Cursor CLI
   bob: false      # set true if you have Bob Shell
   ```

3. Use it:
   ```
   /deep-review                    # review uncommitted changes
   /deep-review last commit        # review last commit
   /deep-review src/auth.py        # audit a specific file
   /deep-review !42                # review GitLab MR #42
   /deep-review #15                # review GitHub PR #15
   /deep-review !42 --re-review    # verify author addressed comments
   /deep-review !42 --design       # explore design alternatives first
   ```

## Tiers

The skill adapts to your toolchain:

| Tier | Tools | Agents | Coverage |
|------|-------|--------|----------|
| **Solo** | Claude only | 3-4 | Full methodology, all phases |
| **Dual** | + Gemini | 6-8 | + cross-model verification |
| **Full** | + 2 families | 10-12 | + platform, architecture review |
| **Max** | + 3+ families | 12-21 | All perspectives, content layer |

Solo is not degraded — it runs every phase with full depth. Additional
models add cognitive diversity (different blind spots), not depth.

## File Structure

```
SKILL.md                    # Main orchestrator (~300 lines)
config.md                   # Your tool configuration
references/
  checklist.md              # 21 analysis dimensions
  patterns.md               # Language-specific security patterns
  examples.md               # Severity calibration examples
  agents.md                 # Agent prompt templates
  perspectives.md           # 21 role perspective prompts
  report.md                 # Report template + verdict criteria
  cross-model.md            # Multi-model dispatch recipes
  mr-review.md              # MR/PR-specific phases
  re-review.md              # Follow-up verification (R0-R4)
scripts/
  shuffle-review-files.py   # Randomized file ordering for agents
evals/
  evals.json                # Evaluation scenarios
```

## Adding Cross-Model Tools

### Gemini (recommended first addition)
Install the [gemini-mcp-tool](https://github.com/nicholaschenai/gemini-mcp-tool)
npm package, configure with your `GEMINI_API_KEY`, and set `gemini: true` in config.md.

### Codex
Install [OpenAI Codex CLI](https://github.com/openai/codex), authenticate,
and set `codex: true`.

### Cursor
Install [Cursor](https://cursor.com), ensure `cursor agent` works in terminal,
set `cursor: true`.

### Bob Shell
Install [Bob Shell](https://bob.ibm.com) (IBM's AI coding CLI with Granite models),
set `bob: true`. Especially valuable for Red Hat / OpenShift / Ansible code.

## Customization

### Project-specific review hints
Create `.review-hints.md` in your repo root with project-specific patterns,
framework behaviors, or domain gotchas. The skill injects this into all agent prompts.

### Security pattern libraries
Place language-specific patterns in `~/.claude/knowledge/security/`:
- `owasp-top10-patterns.md` (Python)
- `golang-security-patterns.md` (Go)
- `cwe-top25-native-patterns.md` (C/C++/Rust)
- `wstg-v42-patterns.md` (Web apps)

### Design exploration
Use `--design` to invoke brainstorming before reviewing. Requires the
`superpowers:brainstorming` skill (fails gracefully if unavailable).

## Design Philosophy

- **Precision over volume** — one confirmed finding beats ten speculative ones
- **Concrete triggers required** — if you can't construct the failure scenario, drop the finding
- **Sibling-check before flagging** — established patterns get downgraded, not flagged
- **Adversarial verification** — every finding goes through a "try to disprove" phase
- **Approach before correctness** — Phase 1.5 checks if the design is sound before Phase 2 checks syntax
- **Risk-tiered** — fast-path for trivial changes, full sweep for complex ones

## Credits

Built on patterns from:
- [RedHatProductSecurity/prodsec-skills](https://github.com/RedHatProductSecurity/prodsec-skills) — security checklists
- [Cloudflare AI Code Review](https://blog.cloudflare.com/ai-code-review) — risk-tiered dispatch (validated across 131K reviews)
- [Cursor BugBot](https://www.cursor.com/blog/bugbot) — randomized file ordering, self-improving feedback loop
- [Anthropic claude-code pr-review-toolkit](https://github.com/anthropics/claude-code) — type invariant scoring
- Karpathy's LLM Council pattern — parallel independent opinions + synthesis

## License

Apache License 2.0 — see [LICENSE](LICENSE).
