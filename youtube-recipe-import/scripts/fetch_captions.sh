#!/usr/bin/env bash
# fetch_captions.sh — Download recipe content from a YouTube video
# Strategy: check description first (fast), fall back to captions only if needed
# Usage: ./fetch_captions.sh <youtube_url> [output_dir]
# Output: plain text at <output_dir>/<video_id>.txt

set -e

URL="$1"
OUTDIR="${2:-/tmp/yt-captions}"

if [ -z "$URL" ]; then
  echo "Usage: $0 <youtube_url> [output_dir]"
  exit 1
fi

# Ensure yt-dlp is installed
if ! command -v yt-dlp &>/dev/null; then
  echo "yt-dlp not found. Installing via Homebrew..."
  brew install yt-dlp
fi

mkdir -p "$OUTDIR"

VIDEO_ID=$(yt-dlp --get-id "$URL" 2>/dev/null || echo "recipe")
OUTFILE="$OUTDIR/${VIDEO_ID}.txt"

echo "Fetching recipe for: $URL  (video_id: $VIDEO_ID)"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Fetch description + title (fast, no video download)
# ─────────────────────────────────────────────────────────────────────────────
DESC_FILE="$OUTDIR/${VIDEO_ID}_desc.txt"
yt-dlp --skip-download --print title --print description "$URL" > "$DESC_FILE" 2>/dev/null || true

# Heuristic: does the description contain a recipe?
# Look for ingredient quantities (numbers + units) and step indicators
RECIPE_IN_DESC=$(python3 - "$DESC_FILE" <<'PYEOF'
import re, sys

with open(sys.argv[1], encoding='utf-8') as f:
    text = f.read().lower()

# Signals that a full recipe is in the description
quantity_pattern = re.compile(r'\b\d+[\s/]*(?:tsp|tbsp|cup|g|ml|kg|lb|oz|piece|cloves?|inch|medium|large|small)\b')
step_pattern = re.compile(r'\b(?:step\s*\d+|method|ingredients?|instructions?|preparation|directions?|how to make|recipe)\b')
ingredient_list = re.compile(r'^\s*[-•*]\s*\d', re.MULTILINE)

qty_matches = len(quantity_pattern.findall(text))
step_matches = len(step_pattern.findall(text))
list_matches = len(ingredient_list.findall(text))
word_count = len(text.split())

# Consider "complete recipe in description" if:
# - has quantity mentions AND step keywords AND reasonable length
if qty_matches >= 3 and step_matches >= 1 and word_count >= 100:
    print("yes")
elif list_matches >= 3 and word_count >= 100:
    print("yes")
else:
    print("no")
PYEOF
)

if [ "$RECIPE_IN_DESC" = "yes" ]; then
  echo "✅ Complete recipe found in description — skipping caption download."
  cp "$DESC_FILE" "$OUTFILE"
  echo "Output (description): $OUTFILE"
  echo "SOURCE=description" >> "$OUTFILE.meta"
  exit 0
fi

echo "Description doesn't contain full recipe. Fetching captions..."

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Fetch subtitles (only if description lacks recipe)
# ─────────────────────────────────────────────────────────────────────────────
yt-dlp \
  --skip-download \
  --write-auto-subs \
  --write-subs \
  --sub-langs "en,en-orig,en-US" \
  --output "$OUTDIR/%(id)s.%(ext)s" \
  "$URL" 2>&1 || true

# Find downloaded subtitle file
SUB_FILE=$(find "$OUTDIR" \( -name "${VIDEO_ID}.en-orig.vtt" \
                          -o -name "${VIDEO_ID}.en.vtt" \) 2>/dev/null | head -1)
if [ -z "$SUB_FILE" ]; then
  SUB_FILE=$(find "$OUTDIR" \( -name "${VIDEO_ID}*.vtt" \
                            -o -name "${VIDEO_ID}*.srt" \) 2>/dev/null | head -1)
fi

if [ -z "$SUB_FILE" ]; then
  echo "⚠️  No subtitles available. Using description as fallback."
  cp "$DESC_FILE" "$OUTFILE"
  echo "Output (description fallback): $OUTFILE"
  echo "SOURCE=description_fallback" >> "$OUTFILE.meta"
  exit 0
fi

echo "Processing subtitles: $SUB_FILE"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Parse VTT/SRT → clean plain text
# ─────────────────────────────────────────────────────────────────────────────
python3 - "$SUB_FILE" "$OUTFILE" <<'PYEOF'
import re, sys

sub_file = sys.argv[1]
out_file = sys.argv[2]

with open(sub_file, encoding='utf-8') as f:
    content = f.read()

# Remove VTT header
content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
# Remove timestamp lines
content = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*\n', '', content)
# Remove inline timestamps
content = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', content)
# Remove HTML/VTT tags
content = re.sub(r'<[^>]+>', '', content)
# Remove sequence numbers on their own line
content = re.sub(r'^\d+\s*$', '', content, flags=re.MULTILINE)
# Collapse blank lines
content = re.sub(r'\n{3,}', '\n\n', content)
# Deduplicate consecutive identical lines
lines = content.split('\n')
deduped, prev = [], None
for line in lines:
    stripped = line.strip()
    if stripped and stripped != prev:
        deduped.append(line)
        prev = stripped
result = '\n'.join(deduped).strip()

with open(out_file, 'w', encoding='utf-8') as f:
    f.write(result)

print(f"Transcript saved: {out_file} ({len(result)} chars, ~{len(result.split())} words)")
PYEOF

echo "SOURCE=captions" >> "$OUTFILE.meta"
echo "Output: $OUTFILE"
