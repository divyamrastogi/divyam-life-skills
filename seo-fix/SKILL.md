---
name: fix
description: Execute the diagnosis - write the JSON-LD schema, the llms.txt, the copy changes and the answer content, then push live via a CMS MCP if one is connected (WordPress/Shopify/Webflow/Sanity). Use when asked to "fix it", "run the fix skill", or implement the diagnosis report.
---

# Fix

Stop at nothing short of done. This skill writes every artifact the diagnosis calls for and, if a CMS MCP is connected, publishes it.

## Inputs
- `seo-reports/diagnosis-<date>.md` (run diagnose first if missing).
- Optional: a CMS MCP (WordPress/Shopify/Webflow/Sanity). Without one, output files + paste-ready instructions instead.

## Steps

1. **Schema**: for each schema fix, write complete JSON-LD. Minimums:
   - Home: `Organization` with `name`, `url`, `logo`, `sameAs` (LinkedIn, Instagram, Google Business, directories — corroboration is the point)
   - Service/product pages: `Service`/`Product` with provider, area served, offers
   - Q&A-style content: `FAQPage` mapped to the real on-page questions
   Validate structure mentally against schema.org; no invented properties.
2. **llms.txt**: write one at the root. Plain markdown: who the brand is, what it does, proof (real numbers only — pull from the site, never invent), key pages with one-line descriptions, how to cite. Short beats long.
3. **Copy changes**: for each copy fix, produce a before/after diff of the exact sentences. Rules: claims must be verifiable, answer-shaped (front-load the answer, then support), no superlatives without proof.
4. **Answer content**: for each unanswered AI question in the diagnosis, draft the answer section (150-300 words): question as H2, direct answer in the first sentence, then evidence. Mark which page each section belongs on.
5. **Publish** (only if a CMS MCP is connected): push schema and copy changes page by page. After each push, fetch the live page and verify the change actually rendered. Anything that fails verification gets reported, not assumed.
6. **Change log**: append every change (or every prepared-but-not-pushed file) to `seo-reports/changes-<date>.md` so the weekly watchdog can correlate changes with movement.

## Output

```
FIX RUN: <domain> — <date>
PUSHED LIVE: <n> changes (verified) / PREPARED: <n> files awaiting manual upload

1. <change> — <pushed+verified | prepared at path>
...
NEXT: set the weekly watchdog (templates/weekly-watchdog.md) to track movement.
```

## Rules
- Never push without verifying the render afterwards.
- Never write a claim into copy or llms.txt that the site/user cannot back up.
- Respect the diagnosis ranking — implement in order, top impact first.
