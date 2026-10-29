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
- **`source_url` — HARD RULE**: the `INSERT INTO recipes (...)` column list MUST include `source_url`, set to the exact same URL as the `-- Source:` header. The header comment alone does nothing — 14 recipes landed on prod with `source_url = NULL` and no cover because of this (fixed by migration `00083_backfill_source_urls_round3.sql`). The cover pipeline (next steps) keys off this column, so a missing `source_url` = a recipe with no image in the app.
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
cd /Users/deeksharastogi/projects/souschef && supabase db query --linked --project-ref yrabrnnahllogoysdvwi \
  -f supabase/seed_<recipe-slug>_<NNN>.sql
```
Success = `{"rows": []}` and no `"_tag": "Error"` in the output. (The Management-API token used here before is expired; the CLI is logged in — `supabase login` if it ever complains.)

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
cd /Users/deeksharastogi/projects/souschef && supabase db query --linked --project-ref yrabrnnahllogoysdvwi "SELECT name, total_time_minutes, source_url, cover_image_url FROM recipes WHERE slug = '<recipe-slug>'"
```

---

### Step 9 — Fetch the Cover Image (required)

Every recipe needs a cover photo or it renders as a grey gradient in the app. The repo's cover pipeline fetches one from `source_url` (og:image for recipe pages, maxres thumbnail for YouTube, a late frame for Instagram reels), normalizes it, uploads it to the `recipe-images` bucket and sets `recipes.cover_image_url` on prod.

```bash
cd /Users/deeksharastogi/projects/souschef && python3 scripts/recipe_media/fetch_covers.py --only <recipe-slug>
```
Expect `[done] processed=1 uploaded=1 failed=0`. Needs `scripts/recipe_media/.service_key` (gitignored, present in the main checkout — copy it into a worktree if you run from one) plus `yt-dlp` + `ffmpeg` for reels.

**Then look at the image before you report it.** Heuristics pick the wrong frame often enough (creator's face, closed pot lid, a site logo):
```bash
curl -s -o /tmp/cover.jpg "https://yrabrnnahllogoysdvwi.supabase.co/storage/v1/object/public/recipe-images/covers/<recipe-slug>.jpg"
```
View `/tmp/cover.jpg`. It must show the finished dish.
- Wrong frame from an Instagram reel → add the slug to `IG_FRAME_FRACTION` (where in the reel the plated shot is, 0–1) and/or `IG_FRAME_CROP_BOTTOM` (talking-head reels: keep the bottom fraction of the frame) in `scripts/recipe_media/fetch_covers.py`, then re-run with `--force`.
- No usable dish photo at the source at all → add the slug to `SKIP_SLUGS` with the reason, null the cover (`UPDATE recipes SET cover_image_url = NULL WHERE slug = '<recipe-slug>'` via the CLI above, and delete `covers/<recipe-slug>.jpg` from the bucket), and tell Divyam the recipe needs a photo. **Null beats wrong.**

Confirm on prod:
```bash
cd /Users/deeksharastogi/projects/souschef && supabase db query --linked --project-ref yrabrnnahllogoysdvwi "SELECT slug, source_url, cover_image_url FROM recipes WHERE slug = '<recipe-slug>'"
```
Both columns must be non-null (unless you deliberately nulled the cover above).

---

### Step 10 — Commit & Push

```bash
cd ~/projects/souschef
git add supabase/seed_<recipe-slug>_<NNN>.sql scripts/recipe_media/cover_progress.json scripts/recipe_media/cover_failures.json
git commit -m "recipe: import <recipe-name> (#<NNN>) [skip ci]"
git push origin <current-branch>
```

Also push skill changes:
```bash
cd ~/clawd/skills && git add . && git commit -m "skill: update recipe-video-import [skip ci]" && git push origin main
```

---

### Step 11 — Report Back to Divyam

- Recipe name + slug
- Source URL + creator
- Ingredient count, phase count, task count
- Confirmed on local + remote
- Cover image: the public URL (after eyeballing it), or "needs photo" + why
- Any ingredients that were newly added to the DB

---

## Notes

- **YouTube Shorts** (`youtube.com/shorts/`) are handled by the same YouTube pipeline — yt-dlp treats them as regular videos
- **Instagram reels** may be rate-limited by yt-dlp — if download fails, try the browser approach (open reel → snapshot → screenshot) as fallback
- **Do NOT hallucinate from low-res frames** — transcript is primary, frames are supplementary
- Always include `[skip ci]` in recipe commits
