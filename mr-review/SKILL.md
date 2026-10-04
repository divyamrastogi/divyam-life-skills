---
name: mr-review
description: Spawn review subagents on a ready MR/PR, address findings, then auto-merge the branch. Use when an agent finishes coding and an MR is ready for review, when asked to "review the PR/MR", "review and merge", or right after opening a PR. Jarvis orchestrates; isolated review subagents hunt bugs and check quality; fixes land on the branch; the PR merges when clean.
---

# MR Review Swarm

You (the orchestrator) drive a ready MR through: **review → fix → merge**. Subagents
review; you triage, coordinate fixes, and merge. Never skip a stage.

## Inputs

- **Repo + cwd** (required) — `cd` there for every command.
- **PR number or branch** (optional) — resolve from the current branch with
  `gh pr view --json number,baseRefName,headRefName,title,url` if not given.
- **Expected base branch** (optional but recommended) — the integration branch the
  PR SHOULD target (usually `main`).
- **Gate command** (optional) — the repo's local quality gates (for Flutter repos:
  `flutter analyze && flutter test`).

## Step 1 — Resolve the MR and CHECK THE BASE BRANCH

1. `gh pr view <n> --json number,title,baseRefName,headRefName,state,url`
2. **Verify `baseRefName` is the expected integration branch.** A stacked branch can
   silently target another feature branch — a wrong-base merge loses work or ships
   an incomplete tree (this exact bug shipped build 11: PR #9's base was a redesign
   branch, not main). If the base is wrong: `gh pr edit <n> --base <expected>`.
   If you cannot determine the expected base, ask the human before proceeding.

## Step 2 — Local gates on the branch

Run the repo's gate command on the working branch. Failing gates = fix first
(yourself or a fix subagent) and re-run. **Review only starts on green gates** —
reviewers must not spend findings on what the gates already catch.

## Step 3 — Collect the review payload

```bash
gh pr diff <n> > /tmp/mr-<n>.diff      # full diff
gh pr view <n> --json title,body       # intent
git log --oneline origin/<base>..HEAD  # commit story
```

If the diff exceeds ~2000 lines, do NOT inline it in subagent tasks — give each
reviewer the repo cwd + PR number and let them fetch sections themselves
(`gh pr diff <n> -- <path>`).

## Step 4 — Spawn review subagents (parallel)

Two reviewers, `sessions_spawn` with `context: "isolated"`, then wait with
`agents_wait` (or `sessions_yield` if they announce). Each task contains: the PR
intent, the diff (or fetch instructions), the gate status, and this exact output
contract:

> Return ONLY a findings list, one finding per line:
> `<severity> | <file>:<line> | <issue> | <suggested fix>`
> Severity: `blocker` (bug / data loss / breaks the feature), `major` (wrong edge
> case, missing test for new behavior, race), `minor`, `nit`. Empty list = approve.

- **Reviewer A — correctness:** trace the changed logic against the intent; hunt
  bugs, unhandled edge cases, state/race issues, regressions to existing behavior.
- **Reviewer B — tests & quality:** new behavior covered by tests? gates actually
  run and green? dead code, leftover debug, naming, consistency with the codebase?

Do not review your own large changes casually — if you authored most of the diff,
still spawn both reviewers; they see it fresh.

## Step 5 — Triage + address findings

1. Merge the two lists; drop duplicates. **blockers and majors must be fixed**;
   minors fixed when trivial; nits recorded only.
2. Fix round: small fixes → do them directly; a pile of findings → spawn one fixer
   subagent with the triaged list (isolated, repo cwd, "edit + run gates + push to
   the same branch").
3. Re-run gates after every fix round. Push.
4. **Re-review only the fix diff** (Step 4 again, scoped to the new commits).
   Maximum **2 review rounds** — if blockers survive round 2, STOP and ask the
   human instead of looping.

## Step 6 — Auto-merge

Merge when ALL hold: gates green locally · zero open blockers/majors · PR CI
checks green (`gh pr checks <n>` — wait for runs to finish; re-check after pushes) ·
base branch verified.

```bash
gh pr merge <n> --squash --delete-branch
```

Use the repo's merge convention if it differs from squash. **After merging, do not
manually build or deploy if the repo has CI that auto-deploys on the base branch**
— that races CI on build numbers (fitcharya: builds 9/10/11 collided exactly this
way). Watch the post-merge CI run instead and report its result.

## Step 7 — Report

One message: verdict per reviewer, findings fixed (with the fix round count),
findings noted (minors/nits), merge SHA, and what fired next (CI/deploy). If you
stopped to ask the human (Step 5 cap or unfixable blocker), say exactly what is
blocking.

## Hard rules

- Never merge with failing gates, failing CI, or an open blocker.
- Never merge into an unverified base branch.
- Never let review rounds exceed 2 without human input.
- Never bypass branch protection or force-merge (`--admin`) — if protection blocks
  the merge, surface it.
