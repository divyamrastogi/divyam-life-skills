---
name: ahaara-swarm
description: Agent swarm orchestration for the Ahaara (SousChef) codebase. Use when Divyam asks (incl. via the Ahaara Dev Bot WhatsApp group) to implement a feature, fix a bug, write tests, or refactor code in the Ahaara Flutter app. Jarvis (OpenClaw, running GLM-5.2) orchestrates and verifies; Claude executes the coding via `claude -p`.
---

# Ahaara Agent Swarm

Jarvis is the orchestrator. You spawn, monitor, verify, and manage Claude Code executors.

## Who does what (model routing)

**You (OpenClaw) stay on your default model — GLM-5.2.** Claude is NOT your model; it is a
CLI subprocess you *delegate to* for souschef coding. The split:

| Role | Who | How |
|------|-----|-----|
| Orchestrate, plan, scope, route | **OpenClaw / GLM-5.2** (you) | directly |
| **All souschef code changes + writing tests** | **Claude** | `claude -p` (light path or swarm — see threshold) |
| Verify: run app, computer-use, video recording, integration tests | **OpenClaw / GLM-5.2** (you) | your skills (`flutter-integration-testing`, `flutter-performance-profiling`, computer-use) |
| WhatsApp I/O (receive request, report result) | **OpenClaw / GLM-5.2** (you) | Ahaara Dev Bot group |

Rule of thumb: **if it writes Dart/SQL/test code in souschef, hand it to Claude. Everything else is you.**

## WhatsApp trigger (Ahaara Dev Bot group `120363425113122951@g.us`)

This group is inbound-allowlisted (`requireMention: false`) — you already receive its messages.
When Divyam sends a coding/test request about souschef there:
1. You (GLM) scope it and pick the execution shape via the threshold below.
2. Claude does the coding via `claude -p`.
3. You (GLM) run the verification stage (Step 6.5) and report back to the same group.

## Execution Threshold — route by size (both paths use Claude)

Every souschef code change is done by Claude. Size only decides the *ceremony*:

**LIGHT PATH** (small change — synchronous `claude -p`, no tmux/PR) when:
- Single-file fix < ~50 lines
- Copy/text change, color, spacing tweak
- Adding a migration with a known pattern
- Divyam says "quick fix" or "just change X"

→ See "Light Path" section below. You shell out to `claude -p` in a worktree, wait, run
`flutter test`, and report the diff. Do **not** hand small changes to GLM to hand-code —
Claude writes all souschef code.

**FULL SWARM** (tmux + worktree + PR + monitor) when:
- New feature or screen (multi-file, likely > 3 files touched)
- Bug that requires tracing through layers (data → repo → provider → UI)
- Refactor or architecture change
- Anything that takes > 20 minutes, or should run async while you do other things

→ Follow the 8-Step Workflow below.

---

## Light Path (small changes — synchronous `claude -p`)

For sub-threshold souschef changes from the Dev Bot group, skip the tmux/registry/PR ceremony.
You (GLM) run Claude synchronously, wait for it, then verify and report.

```bash
SLUG="fix-diet-filter"                     # short kebab description
BRANCH="fix/$(date +%Y-%m-%d)-$SLUG"
WORKTREE="/tmp/ahaara-worktrees/$BRANCH"
SRC="/Users/deeksharastogi/projects/souschef"

git -C "$SRC" worktree add "$WORKTREE" -b "$BRANCH" origin/main
cd "$WORKTREE" && flutter pub get

claude --model claude-sonnet-4-6 --dangerously-skip-permissions \
  --output-format json \
  -p "You are a Flutter/Dart engineer on Ahaara. Read CLAUDE.md at the repo root for
architecture/patterns. TASK: <the WhatsApp request, verbatim>. Make the change AND add/update
tests. Run \`flutter test\` and ensure it passes. Then: git add -A && git commit -m 'fix: <desc>'.
Do NOT push or open a PR — Jarvis verifies first. Report what changed in 2-3 bullets." \
  | tee /tmp/ahaara-claude-$SLUG.json
```

Then **you (GLM)**: run the verification stage (Step 6.5) on the worktree, then report the diff +
test result to the Dev Bot group and ask Divyam whether to push/PR. (Light path commits but does
not push — verification gates the PR.) On a clean change Divyam OKs, push + `gh pr create --fill`.

---

## The 8-Step Workflow (full swarm)

### Step 1: Scope (You — GLM orchestrator)

When Divyam sends a task, think through:
1. What is the goal in one sentence?
2. Which files/layers will change? (data, repo, provider, screen, widget)
3. Can this be parallelised into independent sub-tasks, or must they be sequential?
4. What context does the executor need? (DB schema, existing patterns, Figma links from CLAUDE.md)

Plan inline as GLM — scoping/decomposition is orchestration, your job, not Claude's. If a feature
is large enough that you want a deeper planning pass, spawn a **Claude** planning session (Claude
owns code reasoning), then go to Step 2:
```
sessions_spawn(
  task: "You are a senior Flutter engineer planning an Ahaara feature. Read CLAUDE.md at /Users/deeksharastogi/projects/souschef/CLAUDE.md and the relevant source files. Task: [TASK]. Break into sub-tasks with: (1) goal, (2) files to create/modify, (3) exact prompt for Claude Code executor. Output JSON array of sub-tasks.",
  model: "claude-sonnet-4-6",
  mode: "run"
)
```

For straightforward tasks: plan inline and go straight to Step 2.

### Step 2: Spawn Executor(s)

Each sub-task gets its own worktree + tmux session:

```bash
# 1. Create worktree
BRANCH="feat/TASK-ID-short-description"
WORKTREE="/tmp/ahaara-worktrees/$BRANCH"
git -C /Users/deeksharastogi/projects/souschef worktree add "$WORKTREE" -b "$BRANCH" origin/main

# 2. Install deps in worktree
cd "$WORKTREE" && flutter pub get

# 3. Launch Claude Code in tmux (background, PTY)
tmux new-session -d -s "ahaara-TASK-ID" -c "$WORKTREE" \
  "claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p 'EXECUTOR_PROMPT_HERE'"
```

**Executor prompt template:**
```
You are an expert Flutter/Dart engineer working on Ahaara (a recipe suggestion app).

TASK: [one-sentence goal]

CONTEXT:
- Read CLAUDE.md at the repo root for architecture, patterns, and design links
- Supabase local: 127.0.0.1:54321 | DB: 54322 | password: postgres
- Use Riverpod for state, clean architecture (data/repo/provider/screen)
- Ingredients always come from DB via IngredientRepository — never hardcode
- Run `flutter test` before committing — all tests must pass

FILES TO CHANGE:
[list from planner]

SPECIFIC INSTRUCTIONS:
[detailed steps from planner]

WHEN DONE:
1. Run: flutter test (fix any failures)
2. Commit with message: "feat: [short description]"
3. Push branch and open PR: gh pr create --fill --body "[describe what changed and why]"
4. Run: openclaw system event --text "Done: [task-id] — PR ready for review" --mode now
```

### Step 3: Register the Task

Add to `/Users/deeksharastogi/projects/souschef/.clawdbot/active-tasks.json`:

```json
{
  "id": "feat-TASK-ID",
  "tmuxSession": "ahaara-TASK-ID",
  "agent": "claude-code",
  "model": "claude-sonnet-4-6",
  "description": "One-sentence description",
  "branch": "feat/TASK-ID-short-description",
  "worktree": "/tmp/ahaara-worktrees/feat/TASK-ID-short-description",
  "startedAt": 1234567890000,
  "status": "running",
  "retries": 0,
  "notifyOnComplete": true
}
```

Read the file, append the task, write it back.

### Step 4: Monitor (check-agents.sh)

A cron job runs `.clawdbot/check-agents.sh` every 10 minutes.
It checks:
- Is the tmux session alive?
- Has a PR been opened on the branch?
- Are all GitHub CI checks passing?
- If CI fails → flag for respawn (up to 3 attempts)
- If all pass → mark `ready` and alert you via OpenClaw system event

You then notify Divyam in the Ahaara Dev Bot WhatsApp group.

### Step 5: Mid-Task Redirection

If you notice an agent going the wrong direction (via tmux logs):

```bash
# Check logs
tmux capture-pane -t ahaara-TASK-ID -p | tail -50

# Redirect without killing
tmux send-keys -t ahaara-TASK-ID "Stop. [new direction]. Focus on [specific file]." Enter
```

### Step 6: PR Ready → Notify Divyam

When check-agents.sh emits a "ready" alert, send to Ahaara Dev Bot group (120363425113122951@g.us):

```
✅ PR ready for review!

Task: [description]
Branch: feat/TASK-ID
PR: #NNN — [link]

CI: ✅ passed
Tests: ✅ flutter test passed

Quick summary of what changed:
[2-3 bullet points]
```

### Step 6.5: Verify the change (You — GLM, NOT Claude)

Claude's job ends at "code + tests written, `flutter test` green, PR open." **You (GLM) own
runtime verification** — this is the testing half Divyam wants done by OpenClaw, not Claude.

On the PR branch / worktree, run whichever apply to the change:
- **Behavioral / integration** → `flutter-integration-testing` skill (drive the real flow end-to-end).
- **UI smoothness after UI changes** → `flutter-performance-profiling` skill (jank/scroll/animation).
- **Visual proof for Divyam** → launch the app and capture a **screen/video recording** of the new
  behavior via computer-use (`mcp__computer-use__*`) or the `dart` MCP (`launch_app`, screenshots).
- **Manual click-through** → computer-use to exercise the exact path the request described.

Then post to the Dev Bot group: PR link + CI status + **your** verification result + the
video/screenshot. If verification FAILS, don't sign off — either redirect the executor
(Step 5) or respawn (Step 4 retry), and say so in the group.

Light-path changes: same verification, but since light path didn't push, gate the PR on this —
push + `gh pr create --fill` only after your verification passes and Divyam OKs.

### Step 7: Cleanup After Merge

After Divyam merges:
1. Remove worktree: `git -C /Users/deeksharastogi/projects/souschef worktree remove /tmp/ahaara-worktrees/BRANCH --force`
2. Delete local branch: `git -C /Users/deeksharastogi/projects/souschef branch -d BRANCH`
3. Update task status to `merged` in active-tasks.json
4. A daily cleanup can also be run: prune stale worktrees with `git worktree prune`

## Parallel vs Sequential

**Parallel** (default): Independent features, different files → spawn all at once
**Sequential**: When task B depends on task A's output → wait for A's PR to merge before spawning B

Max parallel agents: 3 (Flutter worktrees are heavier than Node — each needs pub cache)

## Task ID Convention

`YYYY-MM-DD-short-name` → e.g., `2026-02-25-recipe-filter`
Branch: `feat/2026-02-25-recipe-filter`
tmux: `ahaara-2026-02-25-recipe-filter`

For bugs: `fix/2026-02-25-ingredient-crash`
For refactors: `refactor/2026-02-25-provider-cleanup`

## Key Paths

| What | Where |
|------|-------|
| Task registry | `/Users/deeksharastogi/projects/souschef/.clawdbot/active-tasks.json` |
| Monitor script | `/Users/deeksharastogi/projects/souschef/.clawdbot/check-agents.sh` |
| Worktrees | `/tmp/ahaara-worktrees/` |
| Project root | `/Users/deeksharastogi/projects/souschef` |
| CLAUDE.md | `/Users/deeksharastogi/projects/souschef/CLAUDE.md` |
| Notification target | WhatsApp group `120363425113122951@g.us` |

## Proactive Work (Heartbeat)

On heartbeat, scan for opportunities:
- Any open GitHub issues? → could spawn an agent
- Test guardian reports failures? → spawn a fix agent
- Divyam mentioned a feature in chat? → ask if he wants to swarm it

Don't spawn without Divyam's go-ahead for non-trivial tasks. Small fixes are fine to auto-handle.
