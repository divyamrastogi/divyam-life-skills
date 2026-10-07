---
name: install-skill
description: "Use when installing any skill from GitHub or elsewhere, adding a vendored skill to the central skills repo, or fixing agent skill symlinks. Installs for Claude Code, OpenClaw, and zcode together via ~/clawd/skills (central repo) plus the symlink chain — a standing user requirement — and gates every install behind a secret scan."
---

# Install a Skill (Claude Code + OpenClaw + zcode)

Standing requirement (Divyam): when asked to install a skill, install it for **all three agents** via the central repo `~/clawd/skills` (git: divyamrastogi/divyam-life-skills) and the symlink mechanism. Never install into a single agent only.

## Procedure

1. **Clone upstream to /tmp** and inspect: SKILL.md files, LICENSE, shared/, plugin manifests.
2. **Secret scan BEFORE vendoring** (this repo is public; keys leaked once):
   grep -rnE "api[_-]?key|secret|token|password|phx_|pcp_|sbp_|sk-[A-Za-z0-9]{20}|eyJ[A-Za-z0-9_-]{100}" src/ excluding your/placeholder/env examples.
   Real keys -> do not vendor. Publishable keys (sb_publishable_) are fine.
3. **Vendor**: copy skill dir(s) into ~/clawd/skills/<name>/ (no trailing slash on the source path — cp -R dir/ dest dumps contents into the repo root). Multiple skills from one upstream: copy all; inline plugin-only references (${CLAUDE_PLUGIN_ROOT}/shared/x.md) into each SKILL.md so they work outside Claude plugins; keep LICENSE + attribution.
4. **Commit + push** ~/clawd/skills (auto-push rule).
5. **Symlink for all three agents** (rm -f first — ln -s fails on dangling links):
   rm -f ~/.claude/skills/<name> ~/.zcode/skills/<name> ~/.agents/skills/<name>
   ln -s ~/clawd/skills/<name> ~/.agents/skills/<name>
   ln -s ~/clawd/skills/<name> ~/.claude/skills/<name>
   ln -s ~/clawd/skills/<name> ~/.zcode/skills/<name>
6. **Verify through every agent dir** (symlinks can be dangling and still listed):
   [ -e ~/.claude/skills/<name>/SKILL.md ] && [ -e ~/.zcode/skills/<name>/SKILL.md ] && [ -e ~/.agents/skills/<name>/SKILL.md ]

## Decision rules

- ~/.claude/skills relative symlinks resolve from ~/.claude/skills/: use ../../.agents/skills/<name> (two levels up). ../.agents/... is one level short and silently breaks in Claude Code. Absolute paths never break; prefer them.
- After ANY symlink work, run a SKILL.md-resolution loop over all three agent dirs — dangling links make ln fail with "File exists" while still existing as broken links.
- cp -R src/ dest/ (trailing slash) dumps source CONTENTS into dest root — after bulk copies, check git status and remove strays at the repo root.
- install.sh at the repo root is the public one-command installer for OTHER machines — never run it on this Mac (it repoints symlinks to a static clone; this machine develops skills live in ~/clawd/skills).
- Upstream suites that duplicate existing skills: vendor as a complete family (all skills, shared conventions inlined) — partial copies break internal references.

## If secrets were already pushed (recovery)

1. Redact secrets from the current tree.
2. Purge history: git checkout --orphan clean; git add -A; git commit; git branch -D main; git branch -m main; git push --force origin main; git reflog expire --expire=now --all; git gc --prune=now
3. Verify: git log -p origin/main | grep -cE "<secret-pattern>" must be 0.
4. Rotation is still mandatory — purged commits may remain cached on GitHub and in clones. Supabase: rotate the JWT secret (Settings -> API). PostHog: regenerate the personal key. Vendor-specific keys: regenerate in their dashboards.
5. Secret-scanning services (Supabase/PostHog/GitHub) email the owner — rotation closes their alerts.
