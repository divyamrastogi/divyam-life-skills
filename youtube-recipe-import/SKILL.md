---
name: youtube-recipe-import
description: "Import a recipe from a YouTube video into the Ahaara (SousChef) Supabase database. Use when: given a YouTube URL and asked to import, add, or save a recipe from it into Supabase/Ahaara. The skill extracts captions/subtitles from the video, parses the recipe steps and ingredients, and generates + applies a correctly structured SQL seed file matching the Ahaara database schema."
---

# YouTube Recipe Import — Ahaara

Imports a recipe from a YouTube video into the Ahaara Supabase database.

**References:**
- Schema + SQL patterns: `references/schema.md`
- Full ingredient catalogue (119 items): `references/ingredients.md`
- Caption fetch script: `scripts/fetch_captions.sh`

---

## Workflow

### Step 1 — Fetch Recipe Content

```bash
bash ~/clawd/skills/youtube-recipe-import/scripts/fetch_captions.sh "<youtube_url>"
# Output: /tmp/yt-captions/<video_id>.txt
# Source logged in: /tmp/yt-captions/<video_id>.txt.meta
```

The script uses a **description-first strategy**:
1. Fetches the video description (fast, no caption download)
2. Checks if the description already contains a complete recipe (ingredient quantities + steps)
3. **If yes → uses description directly** (skips caption download entirely)
4. If no → downloads and cleans subtitles/captions

Check `.meta` file to see which source was used: `description`, `captions`, or `description_fallback`.

**Install yt-dlp if missing:** `brew install yt-dlp`

---

### Step 2 — Parse the Recipe from Captions

Read the captions file and extract:

1. **Recipe metadata** — name, description, cuisine, diet type, servings, total/active time
2. **Ingredients** — with quantities and units
3. **Steps** — grouped into logical phases (Prep → Cook → Finish/Serve is typical)

**Parsing guidelines:**
- Ignore filler talk, ads, sponsor segments, and commentary
- Focus on ingredients mentioned with quantities and the actual cooking steps
- If the video is in Hindi/mixed language, translate to English
- Infer total_time_minutes from stated cook times; active_time_minutes = total minus passive waits
- Group tasks into 2–4 phases: Prep, Cook (main), Assemble/Finish are common splits
- Passive tasks (boiling, marinating, resting): `task_type = 'passive'`, set `has_timer = true` with alert text
- Active tasks: `task_type = 'active'`

---

### Step 3 — Map Ingredients

Load `references/ingredients.md` and map each recipe ingredient to an existing slug.

**If ingredient exists:** use `get_ing('slug')` — do NOT insert duplicates.

**If ingredient is truly new** (not in catalogue):
- Use `ensure_ingredient()` — it upserts the ingredient if missing, no-op if it already exists
- Returns UUID (but you can ignore it; `get_ing('slug')` still works in the recipe SQL)
- Slug: lowercase hyphenated
- Set `food_type`: `veg` (default), `egg`, `fish`, `seafood`, `poultry`, or `red_meat`
- Choose the correct category slug from: `vegetables`, `dals-legumes`, `rice-grains`, `dairy`, `eggs-nonveg`, `pasta-noodles`, `bread`, `spices`, `sauces`, `others`

```sql
-- Instead of raw INSERT:
SELECT ensure_ingredient('Green Chili Pickle', 'green-chili-pickle', 'sauces', 'veg', false);
-- Works on both local and remote — guaranteed idempotent
```

**NEVER use raw `INSERT INTO ingredients ... ON CONFLICT DO NOTHING`** — that pattern caused remote/local drift. Always use `ensure_ingredient()` for new ingredients.

**Common mappings to watch for:**
- "oil" / "cooking oil" → `oil` or `vegetable-oil`
- "red chilli powder" → `red-chili-powder`
- "jeera" / "cumin" → `cumin-seeds`
- "hing" → `asafoetida`
- "dahi" / "yoghurt" → `curd`
- "methi leaves" → `kasuri-methi` (dried) or add new fresh-methi if fresh

---

### Step 4 — Determine Recipe Number

Check current highest recipe number (111 as of last update — next import = 112):
```bash
ls /Users/deeksharastogi/projects/souschef/supabase/seed_*.sql | grep -oE '_[0-9]+\.sql' | grep -oE '[0-9]+' | sort -n | tail -1
```
Use next available number (e.g., 111).

---

### Step 5 — Generate SQL Seed File

Save to: `/Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql`

Follow the exact pattern from `references/schema.md`. Key rules:

- **`recipe_ingredients`**: One row per unique ingredient. If the same ingredient is used in multiple phases, **combine quantities into one row** with a descriptive `notes` field (e.g., `'2 for marinade, 1 for sauce'`). The UNIQUE(recipe_id, ingredient_id) constraint will reject duplicates.
- **`task_ingredients`**: Use per-step quantities (can reference the same ingredient in different tasks with different quantities — but UNIQUE per task_id+ingredient_id within each task).
- **`{{ingredient-slug}}` in task descriptions**: Embed these so the app can highlight ingredients in the step text. The renderer replaces `{{slug}}` with `"[qty] [IngredientName]"`.
- **NO amounts in step description text — HARD RULE**: Amounts (numeric or parenthetical: `(80g)`, `1/2 tsp`, `2 medium`) must NEVER appear in `phase_tasks.description`. Every amount is expressed ONLY as a `task_ingredients` row referenced by its `{{slug}}` placeholder — the renderer injects the quantity. Hardcoded amounts don't scale with servings and had to be cleaned from prod (souschef migration `00064_strip_stale_step_paren_amounts.sql`).
  - ❌ BAD: `'Whisk {{curd}} (80g) until smooth.'` or `'Add 1/2 tsp {{chili-flakes}}.'`
  - ✅ GOOD: `'Whisk {{curd}} until smooth.'` + `task_ingredients` row `(task_id, get_ing('curd'), 'whisk', 80, 'g', NULL)`
- **Numbered lists for multi-ingredient steps (4+ ingredients)**: Use `E'...\n...'` syntax in SQL so newlines are stored as actual characters. Format: opening action line ending in `:`, then one ingredient per line as `1. {{slug}} — short prep note if needed`, then a closing instruction line. Example:
  ```sql
  E'In a large bowl, combine:\n1. {{chicken}}\n2. {{curd}}\n3. {{ginger-garlic}}\n4. {{salt}}\nMix well and set aside.'
  ```
- **Tips**: Extract specific pro-tips from the video for each task step.
- **Timers**: Set `has_timer = true` and `timer_alert_text` for any passive step with a defined duration.

**UUID format:**
```
Recipe NNN:
  recipe: a1000000-0000-0000-0000-0000000000NNN  (3-digit NNN, zero-padded)
  phase P: b{P}000000-0{NNN}-0000-0000-000000000000
  task T in phase P: c{P}000000-0{NNN}-{T}000-0000-000000000000
```

---

### Step 6 — Apply to Local + Remote

**Local:**
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -f /Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql
```

**Remote (Supabase cloud — project ref: `yrabrnnahllogoysdvwi`):**
```bash
# Write seed SQL to JSON payload and POST to Management API
python3 -c "
import json
with open('/Users/deeksharastogi/projects/souschef/supabase/seed_<recipe-slug>_<NNN>.sql') as f:
    print(json.dumps({'query': f.read()}))
" > /tmp/seed_payload.json

curl -s -X POST "https://api.supabase.com/v1/projects/yrabrnnahllogoysdvwi/database/query" \
  -H "Authorization: Bearer sbp_b5d2dd1d2133068035f5c7f7d3e35aa66e12cd25" \
  -H "Content-Type: application/json" \
  --data @/tmp/seed_payload.json
# Success response: []   (empty array = no rows returned, all good)
```

Check for errors. Common issues:
- `null value in column "ingredient_id"` → slug missing from DB; use `ensure_ingredient()` at top of seed file
- `duplicate key value ... recipe_ingredients_recipe_id_ingredient_id_key"` → merge duplicate ingredient rows
- `duplicate key value ... recipes_slug_key` → change the slug

If Supabase local is not running: `cd /Users/deeksharastogi/projects/souschef && npx supabase start`

---

### Step 7 — Verify (local + remote)

**Local:**
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

**Remote (quick check):**
```bash
python3 -c "import json; print(json.dumps({'query': \"SELECT name, total_time_minutes FROM recipes WHERE slug = '<recipe-slug>'\"}))" > /tmp/q.json
curl -s -X POST "https://api.supabase.com/v1/projects/yrabrnnahllogoysdvwi/database/query" \
  -H "Authorization: Bearer sbp_b5d2dd1d2133068035f5c7f7d3e35aa66e12cd25" \
  -H "Content-Type: application/json" --data @/tmp/q.json
```

Report back: recipe name, ingredient count, phase count, task count — confirmed on both local and remote.

---

### Step 8 — Commit the Seed File

**⚠️ Always include `[skip ci]` in recipe import commits — they're SQL-only, not code changes.**

```bash
cd /Users/deeksharastogi/projects/souschef
git add supabase/seed_<recipe-slug>_<NNN>.sql
git commit -m "recipe: import <recipe-name> (#<NNN>) [skip ci]"
git push origin <current-branch>
```
