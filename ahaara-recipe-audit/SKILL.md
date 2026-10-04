---
name: ahaara-recipe-audit
description: "Audit existing Ahaara recipes for source compliance and quality. Use when Divyam asks to verify recipe sources, clean up unlisted recipes, remove low-quality/single-step recipes, check step descriptions for hardcoded amounts (step-data contract), or do a batch check. Deletes recipes that are NOT from the 3 approved sources OR are too thin/incomplete to be useful; step-contract violations are flagged for cleanup, not deleted."
---

# Ahaara Recipe Source & Quality Audit

Audits recipes in the DB on two criteria and deletes those that fail either:
1. **Source:** must be from one of the 3 approved sites
2. **Quality:** must be detailed enough to be genuinely useful (not single-step stubs)

Plus one **non-destructive** check:

3. **Step-data contract:** step descriptions must not contain hardcoded amounts — violations are flagged for cleanup (Step 1c), never for deletion

## Quality Standard — What's "Detailed Enough"?

A recipe is considered **too thin** (flag for delete + re-import) if:
- It has **only 1 task/step total** across all phases (single-step recipes don't guide the user)
- It has **0 phases** or **0 tasks** (empty stub)
- It has **fewer than 3 recipe_ingredients** (not a real recipe)

These are typically old stub imports that were never fleshed out. **Delete them and re-import from a listed source** if Divyam wants that recipe in the DB.

If a thin recipe is found:
1. Check if a proper version exists on one of the 3 listed sources
2. If yes → delete the thin version, re-import the full one
3. If no → delete and tell Divyam it's not available on any listed source

---

## Approved Sources (Priority Order)

1. **Ranveer Brar** — https://ranveerbrar.com/recipes/ (primary)
2. **Sanjeev Kapoor** — https://www.sanjeevkapoor.com/Recipe/ (first fallback)
3. **Hebbar's Kitchen** — https://hebbarskitchen.com/ (second fallback)
4. **Aruna Vijay** — https://www.instagram.com/arunavijaymasterchef/ (@arunavijaymasterchef on Instagram)

**Rule:** If a recipe can't be found on any of these 4 sources → **delete it from the DB.**

Source must be verifiable (URL must exist and contain the recipe). Existence on a site is enough — the recipe doesn't have to be re-imported unless Divyam requests it.

---

## Credentials

```
Cloud Supabase project: yrabrnnahllogoysdvwi
API URL: https://yrabrnnahllogoysdvwi.supabase.co
Anon key: sb_publishable_nWSo1zqVz-y2RuC2HmZx_A_Gzgzfcyv
Service role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<SERVICE_ROLE-JWT-REDACTED>.Gsl1JWQlFFCGf0sCvRKsD2NMOP_VRsamT4ouRlFLMcI
```

Use the **service role key** for all deletions and writes. The anon key is read-only for recipe data.

---

## Step 1 — Fetch All Recipes + Check Quality

```bash
curl -s "https://yrabrnnahllogoysdvwi.supabase.co/rest/v1/recipes?select=id,name,slug" \
  -H "apikey: sb_publishable_nWSo1zqVz-y2RuC2HmZx_A_Gzgzfcyv" \
  -H "Authorization: Bearer sb_publishable_nWSo1zqVz-y2RuC2HmZx_A_Gzgzfcyv"
```

Or check local seed files for existing sources:

```bash
grep -h "^-- Source:" /Users/deeksharastogi/projects/souschef/supabase/seed_*.sql | sort | uniq
```

### Step 1b — Identify Thin Recipes (Quality Check)

Run this query to find recipes with only 1 or 0 tasks:

```bash
SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<SERVICE_ROLE-JWT-REDACTED>.Gsl1JWQlFFCGf0sCvRKsD2NMOP_VRsamT4ouRlFLMcI"
BASE="https://yrabrnnahllogoysdvwi.supabase.co/rest/v1"

# Fetch all recipes
RECIPES=$(curl -s "$BASE/recipes?select=id,name,slug" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY")

# For each recipe, count tasks and ingredients
# A recipe is "thin" if task count <= 1 OR ingredient count < 3
python3 << 'EOF'
import json, subprocess, urllib.request, urllib.parse

SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<SERVICE_ROLE-JWT-REDACTED>.Gsl1JWQlFFCGf0sCvRKsD2NMOP_VRsamT4ouRlFLMcI"
BASE = "https://yrabrnnahllogoysdvwi.supabase.co/rest/v1"
HEADERS = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}

def fetch(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
    return json.loads(urllib.request.urlopen(req).read())

recipes = fetch("/recipes?select=id,name,slug")
thin = []
for r in recipes:
    rid = r["id"]
    phases = fetch(f"/recipe_phases?recipe_id=eq.{rid}&select=id")
    phase_ids = [p["id"] for p in phases]
    tasks = []
    if phase_ids:
        ids_param = ",".join(phase_ids)
        tasks = fetch(f"/phase_tasks?phase_id=in.({ids_param})&select=id")
    ingredients = fetch(f"/recipe_ingredients?recipe_id=eq.{rid}&select=id")
    task_count = len(tasks)
    ing_count = len(ingredients)
    if task_count <= 1 or ing_count < 3:
        thin.append({**r, "tasks": task_count, "ingredients": ing_count})

print(f"\nThin recipes found: {len(thin)}")
for t in thin:
    print(f"  - {t['name']} ({t['slug']}) — {t['tasks']} tasks, {t['ingredients']} ingredients")
EOF
```

Flag thin recipes for re-import (same delete + source-check workflow as unlisted recipes).

### Step 1c — Step-Data Contract Check (flag for CLEANUP — never delete)

Step descriptions must use `{{slug}}` placeholders with **no hardcoded amounts** (numeric or parenthetical: `(80g)`, `1/2 tsp`, `2 medium`) — every amount lives in a `task_ingredients` row and is injected by the app renderer. Hardcoded amounts don't scale with servings; prod was cleaned once already (souschef migration `00064_strip_stale_step_paren_amounts.sql`).

- ❌ BAD: `'Whisk {{curd}} (80g) until smooth.'` or `'Add 1/2 tsp {{chili-flakes}}.'`
- ✅ GOOD: `'Whisk {{curd}} until smooth.'` + `task_ingredients` row `(task_id, get_ing('curd'), 'whisk', 80, 'g', NULL)`

```bash
python3 << 'EOF'
import json, re, subprocess

ANON = "sb_publishable_nWSo1zqVz-y2RuC2HmZx_A_Gzgzfcyv"
BASE = "https://yrabrnnahllogoysdvwi.supabase.co/rest/v1"

# curl, not urllib — the system Python 3.13 framework build has no CA bundle
# (urllib raises SSL: CERTIFICATE_VERIFY_FAILED); curl uses the OS trust store
def fetch(path):
    out = subprocess.run(
        ["curl", "-s", f"{BASE}{path}",
         "-H", f"apikey: {ANON}", "-H", f"Authorization: Bearer {ANON}"],
        capture_output=True, text=True).stdout
    return json.loads(out)

# Parenthetical AMOUNT right after a placeholder: "{{curd}} (80g)", "{{green-chili}} (5)".
# Requires a digit/fraction inside the paren — prep notes like "{{onion}} (sliced)" are ALLOWED.
paren = re.compile(r"\{\{[a-z0-9-]+\}\}\s*\([^)]*[\d¼½¾⅓⅔⅛]")
# Loose amount + ingredient unit in text: "80g", "1/2 tsp", "¼ cup", "2 cups water".
# Time units deliberately excluded — "5 minutes" in a description is fine.
# NOTE: 'water' IS a tracked ingredient (slug: water) — "2 cups water" must become
# "{{water}}" + a task_ingredients row, same as any other ingredient.
units = re.compile(r"(?i)(?<![a-z0-9])(\d+(?:\.\d+)?|\d+/\d+|[¼½¾⅓⅔⅛])\s*(g|kg|gms?|grams?|ml|l|litres?|tsp|tbsp|teaspoons?|tablespoons?|cups?|pinch(?:es)?)(?![a-z])")

tasks, offset = [], 0
while True:
    page = fetch(f"/phase_tasks?select=id,description,recipe_phases(recipes(name,slug))&limit=1000&offset={offset}")
    tasks += page
    if len(page) < 1000: break
    offset += 1000

flagged = []
for t in tasks:
    d = t.get("description") or ""
    p = [m.group(0) for m in paren.finditer(d)]
    u = [m.group(0) for m in units.finditer(d)]
    if p or u:
        r = ((t.get("recipe_phases") or {}).get("recipes")) or {}
        flagged.append((r.get("slug", "?"), t["id"], p, u, d))

print(f"\nStep-contract violations: {len(flagged)} task(s) across {len({f[0] for f in flagged})} recipe(s)")
print(f"  paren-amounts after placeholder: {sum(1 for f in flagged if f[2])} task(s)")
print(f"  loose amounts in text:           {sum(1 for f in flagged if f[3])} task(s)")
for slug, tid, p, u, d in sorted(flagged):
    print(f"  - {slug} · task {tid}: {p + u}")
    print(f"      {d[:120]}")
EOF
```

The regex catches the common patterns; eyeball flagged lines for false positives (e.g. a legit "cook on 1 low flame" phrasing) before acting. Parenthetical prep notes with no amount (`{{onion}} (sliced)`, `{{curd}} (beaten)`) are allowed and not flagged.

**Violations are cleanup items, never delete triggers.** For each flagged task:
1. Strip the amount from the description text, keeping the `{{slug}}` placeholder — follow the pattern of migration `00064_strip_stale_step_paren_amounts.sql`
2. Verify a `task_ingredients` row carries that quantity; add one if it's missing
3. Ship the fix as a **new** souschef migration (never edit existing ones)

---

## Step 2 — Verify Each Recipe Against Approved Sources

For each recipe, search in source priority order. Due to rate limiting (1 req/sec on Brave), **batch in groups of 4–5** and wait between groups.

**Search pattern:**
```
web_search: site:ranveerbrar.com <recipe name> recipe
web_search: site:sanjeevkapoor.com <recipe name> recipe
web_search: site:hebbarskitchen.com <recipe name> recipe
web_search: site:instagram.com arunavijaymasterchef <recipe name>
```

**Decision:**
- ✅ Found on ANY of the 4 sites → KEEP
- ❌ Not found on any → flag for DELETE

Rate limit mitigation: if you hit 429, wait 10–15 seconds before continuing.

---

## Step 3 — Present Findings to Divyam

Before deleting, summarise both source and quality issues:

```
Recipe audit results:

✅ KEEP (good source + detailed):
- Masala Dosa → ranveerbrar.com
- Soft Idli → hebbarskitchen.com
...

❌ DELETE — Unlisted source (not on Ranveer / Sanjeev Kapoor / Hebbar's):
- Shukto (was: bongeats.com)
- Undhiyu (was: archanaskitchen.com)

⚠️  DELETE — Too thin (single-step or < 3 ingredients):
- Aloo Paratha — 1 task, 4 ingredients → can re-import from ranveerbrar.com
- Plain Rice — 1 task, 1 ingredient → not worth importing

🧹 FLAG — step-contract violations (cleanup via migration, NOT deletion):
- masaledar-chicken-pulao — 2 tasks with hardcoded amounts ('{{curd}} (80g)', '1/2 tsp')

Proceed with all deletions? (Flagged cleanup items will be fixed via a new migration, not deleted.)
```

Wait for confirmation unless Divyam already said "delete if not found / not detailed enough."

---

## Step 4 — Delete Unlisted Recipes

For each recipe to delete, cascade through all related tables **in this exact order**:

```bash
SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<SERVICE_ROLE-JWT-REDACTED>.Gsl1JWQlFFCGf0sCvRKsD2NMOP_VRsamT4ouRlFLMcI"
BASE="https://yrabrnnahllogoysdvwi.supabase.co/rest/v1"
RECIPE_ID="<uuid>"
```

**Step 4a — Get task IDs:**
```bash
# 1. Get phase IDs
PHASE_IDS=$(curl -s "$BASE/recipe_phases?recipe_id=eq.$RECIPE_ID&select=id" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY" \
  | python3 -c "import sys,json; print(','.join(r['id'] for r in json.load(sys.stdin)))")

# 2. Get task IDs from phases
TASK_IDS=$(curl -s "$BASE/phase_tasks?phase_id=in.($PHASE_IDS)&select=id" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY" \
  | python3 -c "import sys,json; print(','.join(r['id'] for r in json.load(sys.stdin)))")
```

**Step 4b — Delete in order:**
```bash
# 1. task_ingredients (deepest child)
curl -s -X DELETE "$BASE/task_ingredients?task_id=in.($TASK_IDS)" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY"

# 2. phase_tasks
curl -s -X DELETE "$BASE/phase_tasks?id=in.($TASK_IDS)" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY"

# 3. recipe_phases
curl -s -X DELETE "$BASE/recipe_phases?recipe_id=eq.$RECIPE_ID" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY"

# 4. recipe_ingredients
curl -s -X DELETE "$BASE/recipe_ingredients?recipe_id=eq.$RECIPE_ID" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY"

# 5. recipe itself (should return 200 + name to confirm)
curl -s -X DELETE "$BASE/recipes?id=eq.$RECIPE_ID" \
  -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Prefer: return=representation" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Deleted:', [r['name'] for r in d])"
```

**For batch deletes** (multiple recipes at once), pass comma-separated IDs:
```
?recipe_id=in.(uuid1,uuid2,...)
?task_id=in.(task1,task2,task3,...)
```

---

## Step 5 — Clean Up Seed Files

After deleting from DB, also remove the corresponding seed files from the repo:

```bash
cd /Users/deeksharastogi/projects/souschef
git rm supabase/seed_<recipe-slug>_replace.sql  # or _NNN.sql
git commit -m "chore: remove <Recipe Name> seed — deleted from DB (unlisted source)"
git push origin main
```

If the seed file was never committed (untracked), just `rm` it instead.

---

## Step 6 — Report Back

```
✅ Audit complete.

Deleted (2):
- Shukto (was sourced from bongeats.com)
- Undhiyu (was sourced from archanaskitchen.com)

Kept (106):
- All verified against Ranveer Brar / Sanjeev Kapoor / Hebbar's Kitchen

Seed files removed. DB is clean.
```

---

## Batch Import Mode

If Divyam provides a list of recipes to add (not just audit), use this skill alongside `ranveer-recipe-import`:

1. For each recipe: search Ranveer Brar first
2. If not found: try Sanjeev Kapoor, then Hebbar's Kitchen
3. If found nowhere: **skip and report** (do not import from unlisted sources)
4. Import found recipes one-by-one using the `ranveer-recipe-import` skill workflow
5. After batch completes, report: ✅ imported / ❌ skipped (not found)

**Rate limiting:** search in batches of 4, pause 10–15s between batches.

---

## Notes

- `recipe_components` table may not exist or may be empty — ignore 400 errors from it during delete
- Verify source by finding the recipe URL in search results, not just the site appearing in results
- Sources added in seed file comments (`-- Source: <url>`) are the canonical record — check those before re-searching
