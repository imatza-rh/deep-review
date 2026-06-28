# Cross-Model Dispatch Reference

> **Contents**: General Principles — Gemini (MCP) — Codex/GPT (CLI) — Cursor Agent (CLI) — Bob/Granite (CLI) — Claude Agents — Tier-Based Counts — Result Validation — Fallback Chain

How to dispatch review agents to each model family. The skill reads `config.md`
to determine which families are available and adapts dispatch accordingly.

**Model names in this file** (e.g., `gpt-5.5`, `claude-4.6-sonnet-medium`) are
examples from mid-2026. Replace with your tool's current default or best model.
Run `codex --help`, `cursor agent models`, or `bob --help` to find available
model IDs. When in doubt, omit the `--model` flag to use the tool's default.

## General Principles

- **Different models catch different bugs.** Claude excels at logic and nuance.
  GPT-5.x catches security patterns Claude normalizes. Gemini has different
  blind spots on nested YAML/config. IBM Granite knows Red Hat/OpenShift
  patterns the others lack. The value is cognitive diversity, not redundancy.
- **Parallel dispatch, not sequential.** All agents launch in ONE message.
  Wall-clock = slowest agent (~2 min), not sum of all agents.
- **Result files, not background agents.** CLI tools write to temp files
  collected via `Read()`. Never use `Agent(run_in_background: true)` for
  review agents — results are lost.

## Gemini (via MCP)

**Direct MCP calls in the main thread** (synchronous — results returned inline):

```
mcp__gemini-mcp-tool__ask-gemini(prompt="Review this diff for bugs, security issues,
and correctness. Report real issues only with severity, file:line, description.
No style suggestions.\n\nDIFF:\n<paste diff>")
```

If you have two Gemini servers, call both with complementary angles:
- Server 1: primary review
- Server 2: contrarian ("what did the first review likely MISS?")

For files IN the project directory, use `@filepath` syntax for large-file context.

**Failure handling:** if Gemini returns an error (429, timeout), note "Gemini: unavailable"
and dispatch an additional Codex or Cursor agent instead.

## Codex / OpenAI GPT (via CLI)

**Background Bash with result capture:**

For PR/MR diff review (pipe the saved diff):
```bash
RESULT_FILE=$(mktemp /tmp/codex-review-XXXXXX) && echo "Review for bugs, security
issues, and correctness. Report real issues only with severity, file:line,
description.

DIFF:
$(cat $DIFF_FILE)" | codex exec -C <REPO_DIR> --model gpt-5.5 --ephemeral \
  --sandbox read-only -o "$RESULT_FILE"
```

For local diff review:
```bash
echo "Review for bugs, security, correctness." | codex exec review --uncommitted \
  --model gpt-5.5 --ephemeral -o /tmp/codex-review-result.txt
```

For file-level review (not a diff):
```bash
echo "Review <FILENAME> for bugs, security, correctness." | codex exec \
  -C <FILE_DIR> --model gpt-5.5 --ephemeral --sandbox read-only -o /tmp/codex-result.txt
```

Run via `Bash(run_in_background: true)`. Collect in Phase 3.7: `Read($RESULT_FILE)`.

**Important:** `codex exec review --uncommitted` only sees LOCAL working tree changes.
For remote PRs not checked out locally, pipe the diff via stdin to `codex exec` instead.

## Cursor Agent (via CLI)

**Background Bash with stream-json output:**

```bash
RESULT_FILE=$(mktemp /tmp/cursor-review-XXXXXX) && timeout 180 cursor agent \
  --print --output-format stream-json --model claude-4.6-sonnet-medium \
  --workspace <FILE_DIR> --trust --approve-mcps \
  "Review <FILENAME> for bugs, security, correctness. Report real issues with
  severity, file:line." > "$RESULT_FILE" 2>&1
```

For PR reviews, use `--workspace <REPO_DIR>` with diff inlined in the prompt
AND changed files named explicitly.

**Key flags:**
- `--output-format stream-json` (required — `json` truncates)
- `--model claude-4.6-sonnet-medium` (100% completion rate, avg 88s)
- `timeout 180` (Sonnet completes in 83-92s avg but variance exists)
- Do NOT use `--mode plan` or `--force` — empirically no benefit for reviews

**Parsing output:**
```python
cat $RESULT_FILE | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line.strip())
        if d.get('type') == 'result' and d.get('subtype') == 'success':
            print(d['result'])
    except: pass
"
```

Run via `Bash(run_in_background: true)`. Collect in Phase 3.7.

**Workspace scoping:** Set `--workspace` to the FILE's directory, not the repo root.
Name the target file explicitly in the prompt to prevent auto-discovery of unrelated files.

**Prompt specificity (MANDATORY):** Generic prompts produce shallow output.
Include 3+ SPECIFIC code patterns from your initial file Read:
- BAD: "Architecture review of FILE."
- GOOD: "Architecture review of FILE. (1) showSlide() is monkey-patched 4 times - trace
  the call chain. (2) BroadcastChannel + postMessage both fire for the same event - are
  messages deduplicated? (3) The frozen mode stores state separately - is it synchronized?"

## Bob Shell / IBM Granite (via CLI)

**Background Bash via Python subprocess:**

Write prompt + diff to a temp file first (shell-safe, no heredoc):
```bash
PROMPT_FILE=$(mktemp /tmp/bob-prompt-XXXXXX)
RESULT_FILE=$(mktemp /tmp/bob-result-XXXXXX)
# Write prompt content to $PROMPT_FILE using the Write tool
python3 -c "import subprocess; p=open('$PROMPT_FILE').read(); \
subprocess.run(['bob','--chat-mode','ask','-p',p], timeout=180)" \
2>&1 | tee "$RESULT_FILE"
```

**Key rules:**
- Always use `timeout 180` (Bob regularly takes 60-90s)
- NEVER use `$(cat file)` in shell arguments — diffs contain shell metacharacters
- NEVER use `capture_output=True` in the subprocess call — it swallows stdout
- Use `mktemp` for ALL temp files (never `$$` or `$RANDOM`)
- For files >500 lines: pre-extract 200-300 lines of key sections into the prompt
- For PR reviews with diff inlined: do NOT use `--hide-intermediary-output` (suppresses all output)
- For file-level reviews where Bob reads workspace: `--hide-intermediary-output` reduces noise

Run via `Bash(run_in_background: true)`. Collect in Phase 3.7: `Read($RESULT_FILE)`.

## Claude Agents

**Foreground anonymous Agent calls:**

```
Agent(subagent_type="claude", prompt="Review <file> for <specific concern>...")
```

Dispatch multiple Agent() calls in ONE response message for parallelism.

**CRITICAL — two patterns that lose results:**
1. `run_in_background: true` — agent goes idle, findings not delivered
2. `name: "..."` on one-shot agents — creates teammate sessions, findings lost

Always use anonymous foreground `Agent()` for review agents.

## Tier-Based Agent Count

| Tier | Phase 0 (background) | Phase 1.5 (approach) | Phase 2.5 (perspectives) |
|------|---------------------|---------------------|-------------------------|
| Solo | — | 1 Claude | 3-4 Claude agents |
| Dual | 1 Gemini or Codex | 1 Claude + 1 cross | 6-8 agents, 2 families |
| Full | Codex + Gemini | 2-3 agents, 2+ families | 10-12 agents, 3+ families |
| Max | Codex + Gemini + Bob + Cursor | 4 agents, 3+ families | 12+ agents, all families |

## Result Validation (MANDATORY)

Before using findings from any CLI agent, check `head -n 5 $RESULT_FILE`:
- Does the output reference the CORRECT filename?
- Are findings about the code under review?
- Is the result from THIS session (check file mtime)?

Discard wrong-target results. Common causes: stale temp files from prior sessions,
CLI auto-discovering the largest file in workspace, `--hide-intermediary-output`
suppressing output.

## Fallback Chain

When a model is unavailable (error, timeout, auth), try the next:
1. Gemini MCP -> Codex CLI -> Cursor CLI -> Bob CLI -> Claude Agent
2. Only declare "CROSS-MODEL UNAVAILABLE" after ALL available families fail
3. A failed dispatch is NOT satisfied — retry or try next family
