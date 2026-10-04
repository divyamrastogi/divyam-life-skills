# Ahaara Supabase Schema Reference

## Connection
- **Local DB:** `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Project:** `/Users/deeksharastogi/projects/souschef`
- **Apply SQL:** `psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -f <file.sql>`
- **API URL:** `http://127.0.0.1:54321` | **API Key:** `Sqt1EDja72zLgkPYZqpnu8wSGYeaebnBsEpi7SNGvEw`

---

## Key Tables

### `recipes`
```sql
id UUID, name TEXT, slug TEXT UNIQUE,
description TEXT, cuisine_type TEXT,
diet_type TEXT,      -- 'vegetarian' | 'eggetarian' | 'non_vegetarian'
difficulty TEXT,     -- 'easy' | 'medium' | 'hard'
total_time_minutes INT,   -- wall-clock time (considers parallelism)
active_time_minutes INT,  -- hands-on time only
servings INT,
cover_image_url TEXT, tips TEXT
```

### `recipe_ingredients` (shopping list / matching)
```sql
recipe_id UUID, ingredient_id UUID,
quantity_value FLOAT,    -- numeric part (NULL if non-numeric)
quantity_unit TEXT,      -- 'tsp' | 'tbsp' | 'cup' | 'g' | 'ml' | 'piece' | 'inch' | 'cloves' | 'medium' | 'large' | 'kg'
quantity_text TEXT,      -- display override: 'to taste', 'a pinch' (use when quantity_value is NULL)
is_optional BOOLEAN, notes TEXT
UNIQUE(recipe_id, ingredient_id)  -- ⚠️ combine if same ingredient appears multiple uses
```

### `recipe_phases`
```sql
id UUID, recipe_id UUID,
phase_number INT,        -- 1, 2, 3... (sequential)
name TEXT,               -- e.g. 'Prep', 'Cook Base', 'Combine & Serve'
description TEXT,        -- 1-line overview
estimated_minutes INT
UNIQUE(recipe_id, phase_number)
```

### `phase_tasks`
```sql
id UUID, phase_id UUID,
task_order INT,          -- sequential within phase
title TEXT,              -- short, action-oriented: 'Chop onions'
description TEXT,        -- full instruction, embed {{ingredient-slug}} for app highlighting — NO amounts in text (see rule below)
task_type TEXT,          -- 'active' (user doing something) | 'passive' (waiting/boiling)
duration_minutes INT,
has_timer BOOLEAN,
timer_alert_text TEXT,   -- e.g. 'Rice is done! Drain now.'
image_url TEXT, tip TEXT
UNIQUE(phase_id, task_order)
```

### `task_ingredients`
```sql
task_id UUID, ingredient_id UUID,
action TEXT,             -- 'chop', 'sauté', 'add', 'blend', 'boil', 'fry', 'garnish', etc.
quantity_value FLOAT, quantity_unit TEXT, quantity_text TEXT
UNIQUE(task_id, ingredient_id)
```

### `ingredients`
```sql
id UUID, name TEXT, slug TEXT UNIQUE,
category_id UUID,
food_type TEXT,  -- 'veg' | 'egg' | 'fish' | 'seafood' | 'poultry' | 'red_meat'
is_common BOOLEAN
```

### `ingredient_categories`
```sql
id UUID, name TEXT, slug TEXT UNIQUE
-- slugs: vegetables, dals-legumes, rice-grains, dairy, eggs-nonveg,
--        pasta-noodles, bread, spices, sauces, others
```

---

## UUID Convention

Current highest recipe number: **110**

```
Recipe:  a1000000-0000-0000-0000-000000000NNN   (NNN = 3-digit recipe number, e.g. 111)
Phase:   b{PHASE}000-{NNN}-0000-0000-000000000000   (PHASE = phase_number padded, NNN = recipe)
Task:    c{PHASE}000-{NNN}-{TASK}000-0000-000000000000  (TASK = task_order padded)
```

Example for recipe 111, phase 2, task 3:
```
recipe:  a1000000-0000-0000-0000-000000000111
phase:   b1000002-0111-0000-0000-000000000000
task:    c1000002-0111-0003-0000-000000000000
```

---

## Helper Function
```sql
get_ing('slug')  -- returns ingredient UUID by slug
-- e.g. get_ing('onion'), get_ing('red-chili-powder')
```

---

## SQL Seed File Pattern

```sql
-- Recipe
INSERT INTO recipes (id, name, slug, description, cuisine_type, diet_type, difficulty, total_time_minutes, active_time_minutes, servings, tips)
VALUES ('...', 'Recipe Name', 'recipe-slug', 'Description.', 'indian', 'vegetarian', 'medium', 30, 20, 4, 'Tips here.');

-- Ingredients (full shopping list — UNIQUE per recipe_id+ingredient_id)
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity_value, quantity_unit, quantity_text, is_optional, notes) VALUES
('recipe-id', get_ing('onion'), 2, 'medium', NULL, false, NULL),
('recipe-id', get_ing('salt'), NULL, NULL, 'to taste', false, NULL);

-- Phase 1
INSERT INTO recipe_phases (id, recipe_id, phase_number, name, description, estimated_minutes)
VALUES ('phase-id', 'recipe-id', 1, 'Prep', 'Prep the vegetables.', 10);

INSERT INTO phase_tasks (id, phase_id, task_order, title, description, task_type, duration_minutes, has_timer, timer_alert_text, tip) VALUES
('task-id', 'phase-id', 1, 'Chop onions', 'Finely chop {{onion}}.', 'active', 3, false, NULL, 'Tip here.');

INSERT INTO task_ingredients (task_id, ingredient_id, action, quantity_value, quantity_unit, quantity_text) VALUES
('task-id', get_ing('onion'), 'chop', 2, 'medium', NULL);
```

### ⚠️ NO amounts in `phase_tasks.description` text

Amounts — numeric or parenthetical — must NEVER appear in step description text. Every amount is expressed ONLY as a `task_ingredients` row; the app renderer replaces `{{slug}}` with the quantity + ingredient name from that row. Hardcoded amounts in text never scale with servings and had to be stripped from prod (souschef migration `00064_strip_stale_step_paren_amounts.sql`).

```sql
-- ❌ BAD: amount hardcoded in description text
('task-id', 'phase-id', 1, 'Chop onions', 'Finely chop {{onion}} (2 medium).', ...);
('task-id', 'phase-id', 2, 'Season', 'Add 1/2 tsp {{chili-flakes}} and mix.', ...);

-- ✅ GOOD: description has only the placeholder; amount lives in task_ingredients
('task-id', 'phase-id', 1, 'Chop onions', 'Finely chop {{onion}}.', ...);
INSERT INTO task_ingredients (task_id, ingredient_id, action, quantity_value, quantity_unit, quantity_text)
VALUES ('task-id', get_ing('onion'), 'chop', 2, 'medium', NULL);
```

---

## Ingredient Handling

**If ingredient exists:** use `get_ing('slug')`

**If ingredient is NEW** (not in the 118-ingredient list), insert it first:
```sql
-- Create new ingredient (find correct category_id first)
INSERT INTO ingredients (name, slug, category_id, food_type, is_common)
VALUES ('Ingredient Name', 'ingredient-slug',
  (SELECT id FROM ingredient_categories WHERE slug = 'vegetables'),  -- pick correct category
  'veg',  -- food_type
  false   -- is_common
);
```

**Slug rules:** lowercase hyphenated, e.g. `coconut-cream`, `spring-onion`

---

## Constraint Checklist
- [ ] `recipe_ingredients`: UNIQUE(recipe_id, ingredient_id) — merge quantities if ingredient repeats
- [ ] `task_ingredients`: UNIQUE(task_id, ingredient_id) — one entry per ingredient per task
- [ ] `recipe_phases`: UNIQUE(recipe_id, phase_number)
- [ ] `phase_tasks`: UNIQUE(phase_id, task_order)
- [ ] `recipes.slug`: UNIQUE, hyphenated
- [ ] `recipe_components`: no self-reference, UNIQUE(parent_recipe_id, component_recipe_id)
