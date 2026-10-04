# divyam-life-skills

Portable `SKILL.md` skills for OpenClaw, Claude Code, and zcode — one command to install everything.

## Install (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/divyamrastogi/divyam-life-skills/main/install.sh | bash
```

What it does:
- clones this repo to `~/.divyam-life-skills`
- symlinks every skill into `~/.agents/skills` (and `~/.claude/skills`, `~/.zcode/skills` if present)
- installs the **pdf-redact** dependency (clones [divyamrastogi/pdf-redact](https://github.com/divyamrastogi/pdf-redact), creates a venv with `reportlab`)
- warns about optional binaries (remindctl, ffmpeg, whisper-cli, gcloud, gh)

## Skills (highlights)
- **karpathy-prompting-tricks** — ASD-STE100 writing, diagrams, throwaway pages, explainer videos
- **interface-design-rules** — interfaces.dev cheat sheet distilled for AI agents
- **pdf-redact** — whitelist-based redaction of card statements (uses the pdf-redact repo + venv)
- **impeccable / taste-skill / emil-design-eng** — design taste & polish suites
- **monthly-rent-invoice**, **mac-calendar**, **google-drive-local**, **stock-alerts**, and more

## Adding a skill
Create `your-skill/SKILL.md` with frontmatter (`name`, `description` with load triggers), commit, push. Runs everywhere on next install.
