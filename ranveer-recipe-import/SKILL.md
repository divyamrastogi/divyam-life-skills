---
name: ranveer-recipe-import
description: "Import a recipe from ranveerbrar.com into the Ahaara (SousChef) Supabase database. Use when Divyam asks to add a recipe to Ahaara. Also handles fallback sources (Sanjeev Kapoor, Hebbar's Kitchen) and source policy enforcement. For bulk audits or deletions of unlisted recipes, see ahaara-recipe-audit skill."
---

# Ranveer Brar Recipe Import — Ahaara

Imports a recipe from https://ranveerbrar.com/recipes/ into the Ahaara Supabase database.

**References (shared with youtube-recipe-import):**
- Schema + SQL patterns: `~/clawd/skills/youtube-recipe-import/references/schema.md`
- Full ingredient catalogue: `~/clawd/skills/youtube-recipe-import/references/ingredients.md`

---

## Source Policy

**Approved sources (priority order):**
1. **Ranveer Brar** — https://ranveerbrar.com/recipes/ (primary)
2. **Sanjeev Kapoor** — https://www.sanjeevkapoor.com/Recipe/ (first fallback)
3. **Hebbar's Kitchen** — https://hebbarskitchen.com/ (second fallback)
4. **Aruna Vijay** — https://www.instagram.com/arunavijaymasterchef/ (@arunavijaymasterchef on Instagram)
5. **Instagram Reels** — public reels from any creator (see below)

**If a recipe is not found on ANY of the 5 sources → do NOT import it. Tell Divyam.**

If Divyam says to manage/clean up existing recipes that came from unlisted sources, use the `ahaara-recipe-audit` skill (handles deletion from DB).

Always record the source URL in the seed file header comment: `-- Source: <url>`

---

## Fetching Recipes from Instagram Reels

Public Instagram reels can be accessed via the OpenClaw browser **without login**. Instagram loads the post content in the DOM even when showing the login dialog overlay — the dialog is just a CSS overlay, not a gate.

### How to fetch an Instagram reel:

```
browser: action=open, url=<instagram_reel_url>
browser: action=snapshot  ← reads caption, comments, hashtags from DOM
browser: action=screenshot ← capture on-screen ingredient overlays from video frame
```

### ✅ Best approach: yt-dlp + Whisper + ffmpeg frames

Use **yt-dlp** to download the reel (works without login for public reels), then:
1. **Audio** → Whisper for full spoken transcript (most accurate for ingredients)
2. **Video** → ffmpeg at 1fps for on-screen text/subtitles
3. Cross-reference both to build the recipe

```bash
# Download reel
yt-dlp '<instagram_reel_url>' -o '/tmp/reel/reel.%(ext)s'

# Transcribe audio
ffmpeg -i /tmp/reel/reel.mp4 -ar 16000 -ac 1 -f wav /tmp/reel/audio.wav -y
whisper-cli --model ~/.clawdbot/models/ggml-base.bin --file /tmp/reel/audio.wav --no-timestamps

# Extract frames at 1fps
mkdir -p /tmp/reel/frames
ffmpeg -i /tmp/reel/reel.mp4 -vf fps=1 /tmp/reel/frames/frame_%03d.jpg -y

# Copy frames to media dir and use image tool to read text
cp /tmp/reel/frames/*.jpg /Users/deeksharastogi/.openclaw/media/
# Then: image tool on batches of frames (max 20 at a time)
```

### Limitations:
- **DM-gated recipes** (creator says "comment Recipe for DM") — actual recipe won't be in post, but audio transcript + frames usually give enough
- **Interacting** (liking, commenting, DMing) requires login

### ⚠️ Do NOT hallucinate from low-res screenshots
Image analysis of in-browser frames is unreliable — always prefer yt-dlp download + Whisper audio. The spoken audio is the most accurate source for ingredients.

### Source URL format for seed file:
```sql
-- Source: https://www.instagram.com/reel/<shortcode>/
-- Creator: @<handle>
```

---

## Workflow

### Step 1 — Search for the Recipe

ranveerbrar.com is JavaScript-rendered, so use web_search to find the recipe:

```
query: "site:ranveerbrar.com <recipe name>"
count: 5
```

**Present results to Divyam** — list titles + URLs found. Ask which one to import if multiple match.

If no results found via search, try fetching the search page directly:
```
web_fetch: https://ranveerbrar.com/?s=<url-encoded-recipe-name>
```

If still nothing on ranveerbrar.com, fall back (see Source Policy above):
1. Search `site:sanjeevkapoor.com <recipe name>`
2. Search `site:hebbarskitchen.com <recipe name>`
3. If none found anywhere → do NOT import; tell Divyam.

---

### Step 2 — Fetch the Recipe Page

Once Divyam confirms (or there's a clear single match), fetch the recipe URL:

```
web_fetch: <recipe_url>
maxChars: 15000
```

Extract:
1. **Recipe metadata** — name, description, cuisine, diet type, servings, prep time, cook time
2. **Ingredients** — with quantities and units
3. **Method/Steps** — numbered steps from the recipe

If web_fetch returns incomplete content (JS-rendered page), use browser:
```
browser: action=open, url=<recipe_url>
browser: action=snapshot  (to extract text content)
```

---

### Step 3 — Parse + Structure the Recipe

From the fetched content, extract:

- **name**: Recipe title (e.g. "Dal Makhani")
- **slug**: lowercase-hyphenated (e.g. `dal-makhani`)
- **description**: 1-2 sentence summary
- **cuisine_type**: `indian` (default for Ranveer Brar), or `mughlai`, `punjabi`, etc. → use `indian`
- **diet_type**: `vegetarian`, `non_vegetarian`, `vegan`, `eggetarian`
- **difficulty**: `easy`, `medium`, `hard`
- **total_time_minutes**: prep_time + cook_time
- **active_time_minutes**: total minus passive waits (soaking, marinating, simmering)
- **servings**: from recipe

**Group steps into 2–4 logical phases:**
- Typical: Prep → Cook → Finish & Serve
- Passive steps (soak, marinate, simmer, rest): `task_type = 'passive'`, `has_timer = true`
- Active steps: `task_type = 'active'`

**Add tips** — Ranveer Brar usually has chef's tips; capture them per step.

---

### Step 4 — Map Ingredients

Load `~/clawd/skills/youtube-recipe-import/references/ingredients.md` and map each ingredient to an existing DB slug using `get_ing('slug')`.

**Common Indian ingredient mappings:**
- "oil" / "cooking oil" → `oil`
- "red chilli powder" → `red-chili-powder`
- "jeera" / "cumin seeds" → `cumin-seeds`
- "hing" / "asafoetida" → `asafoetida`
- "dahi" / "yoghurt" / "curd" → `curd`
- "methi leaves" (dried) → `kasuri-methi`
- "haldi" → `turmeric`
- "dhaniya powder" → `coriander-powder`
- "kali mirch" → `black-pepper`
- "tej patta" → `bay-leaf`
- "chakri phool" → `star-anise`

**For truly new ingredients:** use `ensure_ingredient()` at the top of the seed file:
```sql
SELECT ensure_ingredient('Ingredient Name', 'ingredient-slug', 'category-slug', 'veg', false);
```
Categories: `vegetables`, `dals-legumes`, `rice-grains`, `dairy`, `eggs-nonveg`, `pasta-noodles`, `bread`, `spices`, `sauces`, `others`

**NEVER use raw INSERT for ingredients.** Always use `ensure_ingredient()`.

---

### Step 5 — Determine Recipe Number

```bash
ls /Users/deeksharastogi/projects/souschef/supabase/seed_*.sql | grep -oE '_[0-9]+\.sql' | grep -oE '[0-9]+' | sort -n | tail -1
```
Use next available number (e.g. if highest is 112, use 113).

---

### Step 6 — Generate SQL Seed File

Save to: `/Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql`

**UUID format:**
```
Recipe NNN:
  recipe:          a1000000-0000-0000-0000-0000000000NNN  (3-digit NNN, zero-padded)
  phase P:         b{P}000000-0{NNN}-0000-0000-000000000000
  task T, phase P: c{P}000000-0{NNN}-{T}000-0000-000000000000
```

**Key rules (same as youtube-recipe-import):**
- `recipe_ingredients`: one row per unique ingredient; combine if the same ingredient is used multiple times — add a descriptive `notes` field
- `task_ingredients`: per-step quantities; same ingredient can appear in different tasks
- Embed `{{ingredient-slug}}` in task descriptions — renderer replaces with "[qty] IngredientName"
- **NO amounts in step description text — HARD RULE**: amounts (numeric or parenthetical: `(80g)`, `1/2 tsp`, `2 medium`) must NEVER appear in `phase_tasks.description`. Every amount goes ONLY in a `task_ingredients` row referenced by its `{{slug}}` placeholder — the renderer injects the quantity. Hardcoded amounts don't scale with servings (prod cleanup: migration `00064_strip_stale_step_paren_amounts.sql`).
  - ❌ BAD: `'Whisk {{curd}} (80g) until smooth.'` or `'Add 1/2 tsp {{chili-flakes}}.'`
  - ✅ GOOD: `'Whisk {{curd}} until smooth.'` + `task_ingredients` row `(task_id, get_ing('curd'), 'whisk', 80, 'g', NULL)`
- For steps with 4+ ingredients, use numbered list format with `E'...\n...'` syntax
- Passive steps: set `has_timer = true` + `timer_alert_text`
- Add `tip` to each task — draw from Ranveer Brar's chef tips or add sensible ones

---

### Step 7 — Apply to Local + Remote

**Local Supabase:**
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -f /Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql
```
If not running: `cd /Users/deeksharastogi/projects/souschef && npx supabase start`

**Remote (Supabase cloud — project ref: `yrabrnnahllogoysdvwi`):**
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
Success = empty array `[]` response.

**Common errors:**
- `null value in column "ingredient_id"` → slug missing; add `ensure_ingredient()` at top
- `duplicate key ... recipe_ingredients_recipe_id_ingredient_id_key` → merge duplicate rows
- `duplicate key ... recipes_slug_key` → change the slug

---

### Step 8 — Commit the Seed File

After verifying locally and on remote, commit and push the seed file.

**⚠️ Always include `[skip ci]` in recipe import commits — they're SQL-only, not code changes.**

```bash
cd /Users/deeksharastogi/projects/souschef
git add supabase/seed_<recipe-slug>_<NNN>.sql
git commit -m "recipe: import <recipe-name> (#<NNN>) [skip ci]"
git push origin <current-branch>
```

Also push to the skills repo after any skill edits:
```bash
cd /Users/deeksharastogi/clawd/skills && git add . && git commit -m "skill: recipe import update [skip ci]" && git push origin main
```

---

### Step 9 — Verify

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

**Report back to Divyam:**
- Recipe name + slug
- Ingredient count, phase count, task count
- Confirmed on local + remote
- Link to the source recipe on ranveerbrar.com

---

## Silent Clean Runs

This skill is triggered by Divyam — no silent/heartbeat runs. Always reply with results.
