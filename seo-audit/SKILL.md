---
name: audit
description: Crawl a website and produce a scored SEO audit (P0/P1/P2 findings) using the Search Console MCP for real ranking data, free Google APIs for Core Web Vitals, and direct crawling for technical checks. Use when asked to "audit", "run the audit", or "check what's broken" on a site.
---

# Audit

Produce a scored technical and content audit of the target site. Findings, not vibes: every issue gets a severity, evidence, and a one-line fix direction.

## Inputs
- Target domain (ask if not given).
- Search Console MCP connected (tools available for queries/pages). If missing, say so and continue with crawl-only checks.

## Steps

1. **Pull real search data** (Search Console MCP): top 50 queries and pages by clicks for the last 90 days vs prior 90. Flag:
   - Pages with falling clicks at stable position (content decay)
   - Two of your pages ranking for the same query (cannibalisation)
   - Queries at position 5-15 with high impressions (quick wins)
2. **Crawl the site**: fetch the homepage, sitemap.xml, robots.txt, llms.txt, and the top 10 pages from step 1. For each page check:
   - Title and meta description present, unique, right length (titles 50-60 chars, descriptions 140-160)
   - Exactly one H1; heading hierarchy sane
   - JSON-LD structured data present and valid (Organization on home, Article/Product/FAQ where relevant)
   - Canonical tags, image alt text, internal links in and out
   - llms.txt exists at the root (if not: P1, AI crawlers get no guidance)
   - robots.txt does not block AI crawlers you WANT (GPTBot, Google-Extended, PerplexityBot, ClaudeBot) unless intentional
3. **Core Web Vitals** (free, no key needed for low volume): for the top 5 pages hit
   `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<page>&strategy=mobile`
   and read LCP, INP, CLS from the CrUX field data. Failing CWV on money pages = P0.
4. **Score and rank**: every finding gets:
   - **P0** — actively losing you traffic or blocking indexing/AI access
   - **P1** — meaningful gap vs competitors (missing schema, no llms.txt, decay)
   - **P2** — hygiene (alt text, minor titles)

## Output

A single report, this exact shape:

```
AUDIT: <domain> — <date>
SCORE SUMMARY: X P0 · Y P1 · Z P2

P0 FINDINGS
1. <finding> — evidence: <data> — fix: <one line>
...
QUICK WINS (from real GSC data)
1. "<query>" at position <n>, <impressions> impressions — <action>
...
```

Save the report to `seo-reports/audit-<date>.md` in the project. The diagnose skill consumes it.

## Rules
- Never invent numbers. Every position, click count and CWV value comes from the MCP or the API response.
- If a check cannot run (no GSC access, API error), list it under "NOT CHECKED" rather than skipping silently.
