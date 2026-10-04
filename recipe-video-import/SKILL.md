---
name: recipe-video-import
description: "Auto-import recipes from any video link (Instagram reel, YouTube video/short, or direct MP4) into the Ahaara Supabase database. NO NEED TO ASK — when Divyam sends a recipe video link in any chat, immediately import it. Detects source type, extracts transcript + frames, parses ingredients & steps, generates migration SQL, commits. Use whenever Divyam sends a food/recipe video link."
---

# Recipe Video Import — Ahaara

Unified skill to import recipes from **any video source** into the Ahaara (SousChef) Supabase database.

## ⚡ AUTO-IMPORT RULE

**When Divyam sends an Instagram reel, YouTube video/short, or any recipe video link → import it immediately.** Do NOT ask "want me to add this?" — just do it. Transcribe, parse, generate migration, commit. Only ask if something is ambiguous (can't determine if it's a recipe, missing critical info, etc.).

**Supported sources:**
- YouTube videos & Shorts (`youtube.com`, `youtu.be`)
- Instagram Reels (`instagram.com/reel/...`)
- Direct video URLs (`.mp4`, `.mov`)

**Shared references** (from youtube-recipe-import skill):
- Schema + SQL patterns: `~/clawd/skills/youtube-recipe-import/references/schema.md`
- Full ingredient catalogue: `~/clawd/skills/youtube-recipe-import/references/ingredients.md`

---

## Quick Reference — Detection

| URL pattern | Source | Strategy |
|---|---|---|
| `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/` | YouTube | `fetch_captions.sh` → description-first, fallback captions |
| `instagram.com/reel/` | Instagram | yt-dlp download → Whisper transcript + ffmpeg frames |
| `.mp4`, `.mov` URL | Direct | yt-dlp/ffmpeg download → Whisper + frames |
| Other | Try yt-dlp | Download → Whisper + frames |

---

## Workflow

### Step 1 — Detect Source & Download Content

```bash
bash ~/clawd/skills/recipe-video-import/scripts/fetch_recipe.sh "<url>"
```

This script auto-detects the source and runs the optimal pipeline:
- **YouTube**: Uses `fetch_captions.sh` from youtube-recipe-import (description-first, captions fallback)
- **Instagram / Direct / Other**: Downloads video via yt-dlp → Whisper audio transcript + ffmpeg frame extraction

**Output directory:** `/tmp/recipe-import/`
- `transcript.txt` — full spoken transcript (or YouTube captions/description)
- `frames/` — extracted video frames at key moments
- `video.mp4` — downloaded video (Instagram/direct only)
- `meta.json` — source type, video ID, metadata

**Install if missing:** `brew install yt-dlp ffmpeg whisper-cpp`

---

### Step 2 — Analyze Video Frames (Instagram & video sources)

For Instagram reels and video sources, frames are automatically extracted. Use the `image` tool to analyze them for on-screen ingredient lists, measurements, and step text:

```
image: images=[frame paths], prompt="Extract all recipe information visible in these frames: ingredient names, quantities, measurements, step numbers, cooking instructions. List everything you can read."
```

**Cross-reference** frame text with the audio transcript for accuracy — the transcript is the primary source, frames fill gaps.

---

### Step 3 — Parse the Recipe

Read the transcript (and frame analysis if available). Extract:

1. **Recipe metadata** — name, description, cuisine, diet type, servings, total/active time
2. **Ingredients** — with quantities and units (cross-reference transcript + frames)
3. **Steps** — grouped into logical phases (Prep → Cook → Finish/Serve)

**Parsing guidelines:**
- Ignore filler talk, ads, sponsor segments, commentary
- Focus on ingredients with quantities and actual cooking steps
- Hindi/mixed language → translate to English
- Infer `total_time_minutes` from stated cook times; `active_time_minutes` = total minus passive waits
- Group into 2–4 phases (Prep, Cook main, Assemble/Finish typical)
- Passive tasks (boiling, marinating, resting): `task_type = 'passive'`, `has_timer = true`
- Active tasks: `task_type = 'active'`

---

### Step 4 — Map Ingredients

Load `~/clawd/skills/youtube-recipe-import/references/ingredients.md` and map each ingredient to an existing DB slug.

**Existing ingredient →** `get_ing('slug')` — no duplicates.

**Truly new ingredient →** `ensure_ingredient()`:
```sql
SELECT ensure_ingredient('Ingredient Name', 'ingredient-slug', 'category-slug', 'veg', false);
```
Categories: `vegetables`, `dals-legumes`, `rice-grains`, `dairy`, `eggs-nonveg`, `pasta-noodles`, `bread`, `spices`, `sauces`, `others`

**Common mappings:**
- "oil"/"cooking oil" → `oil` or `vegetable-oil`
- "red chilli powder" → `red-chili-powder`
- "jeera"/"cumin" → `cumin-seeds`
- "hing" → `asafoetida`
- "dahi"/"yoghurt" → `curd`
- "methi leaves" (dried) → `kasuri-methi`
- "haldi" → `turmeric`
- "dhaniya powder" → `coriander-powder`

**NEVER raw INSERT ingredients.** Always `ensure_ingredient()`.

---

### Step 5 — Determine Recipe Number

```bash
ls /Users/deeksharastogi/projects/souschef/supabase/seed_*.sql | grep -oE '_[0-9]+\.sql' | grep -oE '[0-9]+' | sort -n | tail -1
```
Use next available number.

---

### Step 6 — Generate SQL Seed File

Save to: `/Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql`

Follow patterns from `~/clawd/skills/youtube-recipe-import/references/schema.md`.

**UUID format:**
```
Recipe NNN (3-digit, zero-padded):
  recipe:          a1000000-0000-0000-0000-0000000000NNN
  phase P:         b{P}000000-0{NNN}-0000-0000-000000000000
  task T, phase P: c{P}000000-0{NNN}-{T}000-0000-000000000000
```

**Key rules:**
- `recipe_ingredients`: ONE row per unique ingredient. Same ingredient in multiple phases → combine quantities, add `notes`
- `task_ingredients`: per-step quantities; same ingredient OK in different tasks
- Embed `{{ingredient-slug}}` in task descriptions — renderer replaces with "[qty] IngredientName"
- **NO amounts in step description text — HARD RULE**: amounts (numeric or parenthetical: `(80g)`, `1/2 tsp`, `2 medium`) must NEVER appear in `phase_tasks.description`. Every amount goes ONLY in a `task_ingredients` row referenced by its `{{slug}}` placeholder — the renderer injects the quantity. Hardcoded amounts don't scale with servings (prod cleanup: migration `00064_strip_stale_step_paren_amounts.sql`).
  - ❌ BAD: `'Whisk {{curd}} (80g) until smooth.'` or `'Add 1/2 tsp {{chili-flakes}}.'`
  - ✅ GOOD: `'Whisk {{curd}} until smooth.'` + `task_ingredients` row `(task_id, get_ing('curd'), 'whisk', 80, 'g', NULL)`
- 4+ ingredient steps → numbered list with `E'...\n...'` syntax
- Passive steps → `has_timer = true` + `timer_alert_text`
- Add `tip` per task from video or sensible defaults

**Header comment with source:**
```sql
-- Recipe: <name>
-- Source: <url>
-- Creator: <handle or channel>
-- Imported: <date>
```

---

### Step 7 — Apply to Local + Remote

**Local:**
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -f /Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql
```
If not running: `cd ~/projects/souschef && npx supabase start`

**Remote (project ref: `yrabrnnahllogoysdvwi`):**
```bash
python3 -c "
import json
with open('/Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql') as f:
    print(json.dumps({'query': f.read()}))
" > /tmp/seed_payload.json

curl -s -X POST "https://api.supabase.com/v1/projects/yrabrnnahllogoysdvwi/database/query" \
  -H "Authorization: Bearer sbp_b5d2dd1d2133068035f5c7f7d3e35aa66e12cd25" \
  -H "Content-Type: application/json" \
  --data @/tmp/seed_payload.json
```
Success = `[]`.

**Common errors:**
- `null value in column "ingredient_id"` → missing slug; add `ensure_ingredient()` at top
- `duplicate key ... recipe_ingredients` → merge duplicate ingredient rows
- `duplicate key ... recipes_slug_key` → change the slug

---

### Step 8 — Verify

```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c "
  SELECT r.name, r.total_time_minutes, r.diet_type,
    COUNT(DISTINCT ri.id) AS ingredients,
    COUNT(DISTINCT rp.id) AS phases,
    COUNT(DISTINCT pt.id) AS tasks,
    COUNT(DISTINCT ti.id) AS task_ingredients
  FROM recipes r
  LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
  LEFT JOIN recipe_phases rp ON rp.recipe_id = r.id
  LEFT JOIN phase_tasks pt ON pt.phase_id = rp.id
  LEFT JOIN task_ingredients ti ON ti.task_id = pt.id
  WHERE r.slug = '<recipe-slug>'
  GROUP BY r.id;
"
```

Also quick-check remote:
```bash
python3 -c "import json; print(json.dumps({'query': \"SELECT name, total_time_minutes FROM recipes WHERE slug = '<recipe-slug>'\"}))" > /tmp/q.json
curl -s -X POST "https://api.supabase.com/v1/projects/yrabrnnahllogoysdvwi/database/query" \
  -H "Authorization: Bearer sbp_b5d2dd1d2133068035f5c7f7d3e35aa66e12cd25" \
  -H "Content-Type: application/json" --data @/tmp/q.json
```

---

### Step 9 — Commit & Push

```bash
cd ~/projects/souschef
git add supabase/seed_<recipe-slug>_<NNN>.sql
git commit -m "recipe: import <recipe-name> (#<NNN>) [skip ci]"
git push origin <current-branch>
```

Also push skill changes:
```bash
cd ~/clawd/skills && git add . && git commit -m "skill: update recipe-video-import [skip ci]" && git push origin main
```

---

### Step 10 — Report Back to Divyam

- Recipe name + slug
- Source URL + creator
- Ingredient count, phase count, task count
- Confirmed on local + remote
- Any ingredients that were newly added to the DB

---

## Notes

- **YouTube Shorts** (`youtube.com/shorts/`) are handled by the same YouTube pipeline — yt-dlp treats them as regular videos
- **Instagram reels** may be rate-limited by yt-dlp — if download fails, try the browser approach (open reel → snapshot → screenshot) as fallback
- **Do NOT hallucinate from low-res frames** — transcript is primary, frames are supplementary
- Always include `[skip ci]` in recipe commits
