#!/usr/bin/env bash
# divyam-life-skills — one-command installer
#   curl -fsSL https://raw.githubusercontent.com/divyamrastogi/divyam-life-skills/main/install.sh | bash
set -e
REPO="https://github.com/divyamrastogi/divyam-life-skills.git"
DEST="$HOME/.divyam-life-skills"

echo "▸ cloning skills repo…"
if [ -d "$DEST/.git" ]; then git -C "$DEST" pull -q; else git clone -q --depth 1 "$REPO" "$DEST"; fi

echo "▸ linking skills into agents…"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.zcode/skills"
linked=0
for d in "$DEST"/*/; do
  [ -f "$d/SKILL.md" ] || continue
  name=$(basename "$d")
  ln -sfn "$d" "$HOME/.agents/skills/$name"
  [ -e "$HOME/.claude/skills/$name" ] || ln -s "$HOME/.agents/skills/$name" "$HOME/.claude/skills/$name"
  [ -e "$HOME/.zcode/skills/$name" ] || ln -s "$HOME/.agents/skills/$name" "$HOME/.zcode/skills/$name"
  linked=$((linked+1))
done
echo "  ✓ $linked skills → ~/.agents/skills (+ ~/.claude/skills, ~/.zcode/skills)"

echo "▸ dependency: pdf-redact (redaction skill backend)…"
PR="$HOME/projects/pdf-redact"
if [ ! -d "$PR" ]; then
  git clone -q --depth 1 https://github.com/divyamrastogi/pdf-redact.git "$PR"
fi
if [ ! -d "$PR/venv" ]; then
  echo "  creating python venv + reportlab…"
  python3 -m venv "$PR/venv" && "$PR/venv/bin/pip" -q install reportlab
fi
echo "  ✓ pdf-redact ready: $PR (venv: $PR/venv)"

echo "▸ optional binaries (install if you need these skills):"
for b in remindctl ffmpeg whisper-cli gcloud gh; do
  command -v "$b" >/dev/null 2>&1 || echo "  ◦ $b not found"
done

echo ""
echo "✅ Done. Restart your agent(s) and the skills load automatically."
