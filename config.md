# Deep Review Configuration

Declare your available tools below. The skill adapts its agent dispatch
based on what you have. **Claude is always available** — the skill works
with Claude alone (Solo tier). Additional tools unlock more coverage.

## Available Models

Set each to `true` or `false`:

```yaml
claude: true          # Always true — the skill runs on Claude Code

gemini: false         # Gemini MCP server (gemini-mcp-tool or gemini-35-flash)
                      # Install: npm package `gemini-mcp-tool`, needs GEMINI_API_KEY
                      # Value: different training data catches bugs Claude normalizes

codex: false          # OpenAI Codex CLI (`codex exec`)
                      # Install: npm install -g @openai/codex
                      # Value: GPT-5.x security review, adversarial testing

cursor: false         # Cursor Agent CLI (`cursor agent --print`)
                      # Install: cursor.com, `cursor agent` in terminal
                      # Value: architecture review, blast radius analysis

bob: false            # Bob Shell / IBM Granite (`bob --chat-mode ask`)
                      # Install: curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash
                      # Value: Red Hat / OpenShift / Ansible platform knowledge
```

## Tier Resolution

The skill reads this config at Phase 0 and selects a tier:

| Tier | Requirement | Agents | What you get |
|------|------------|--------|-------------|
| **Solo** | Claude only | 3-6 | Full methodology, all phases, Claude perspectives (3 code + up to 3 content for deliverables) |
| **Dual** | Claude + 1 other | 6-10 | + cross-model verification, contrarian angle |
| **Full** | Claude + 2 others | 10-14 | + platform, architecture, security specialists |
| **Max** | Claude + 3+ others | 12-21 | All perspectives across all model families |

Solo is NOT degraded — it runs every phase with full depth. Additional
models add COVERAGE (different blind spots), not depth.

## Optional: Gemini MCP Server Names

If you have Gemini configured, specify your MCP server tool prefix(es):

```yaml
gemini_servers:
  - mcp__gemini-mcp-tool__ask-gemini
  # - mcp__gemini-35-flash__ask-gemini   # uncomment if you have a second
```

## Optional: Custom Review Hints

If your project has a `.review-hints.md` in the repo root, the skill
reads it and injects its content into all agent prompts. Use this for
project-specific patterns, framework behaviors, or domain gotchas that
generic reviewers miss.

## Optional: Security Pattern Libraries

Place language-specific security patterns in your knowledge directory:
- `~/.claude/knowledge/security/owasp-top10-patterns.md` (Python)
- `~/.claude/knowledge/security/golang-security-patterns.md` (Go)
- `~/.claude/knowledge/security/cwe-top25-native-patterns.md` (C/C++/Rust)
- `~/.claude/knowledge/security/wstg-v42-patterns.md` (Web apps)

The skill loads the matching file when it detects that language in the diff.
If the files don't exist, the skill uses the built-in `references/patterns.md`.

## Allowed Tools (SKILL.md frontmatter)

The `allowed-tools` list in SKILL.md covers Claude-native tools and git
commands. If you enable cross-model tools, add their tool prefixes:

```yaml
# Gemini MCP:
mcp__gemini-mcp-tool__ask-gemini
mcp__gemini-35-flash__ask-gemini

# Codex, Cursor, Bob run via Bash — already covered by Bash(codex:*) etc.
# Add to allowed-tools if your setup needs explicit patterns:
Bash(codex:*)
Bash(cursor:*)
Bash(timeout *bob:*)
Bash(bob:*)
```
