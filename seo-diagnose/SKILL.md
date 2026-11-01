---
name: diagnose
description: Merge the audit and visibility reports into the 15 fastest fixes ranked by effort vs impact, plus the exact questions people ask AI that the site never answers. Use when asked "what do we fix first", "run diagnose", or after audit + visibility have produced reports.
---

# Diagnose

Reports are not plans. This skill turns the audit and visibility reports into a ranked, do-this-first plan a non-SEO can execute.

## Inputs
- `seo-reports/audit-<date>.md` and `seo-reports/visibility-<date>.md` (run those skills first if missing).
- DataForSEO MCP for question mining.

## Steps

1. **Merge findings**: pull every P0/P1 from the audit and every "why you're skipped" reason from the visibility report into one list. Dedupe (a missing schema finding and a "no corroboration" skip-reason may share one fix).
2. **Mine the unanswered questions** (DataForSEO): for the site's top 3 topics, pull People Also Ask questions and related/long-tail queries with question modifiers (how, best, vs, worth it, near me). Cross-check each against the site: does ANY page answer it? Collect the misses — these are the questions people ask AI where you are silent.
3. **Rank by effort vs impact**: score each candidate fix Impact (1-5: traffic/citation potential, from real impressions and visibility gaps) and Effort (1-5: one-line change → new content). Sort by Impact/Effort descending. Take the top 15.
4. **Write the plan**: each fix gets: what, why (evidence from the reports), how (concrete: "add Organization JSON-LD with sameAs links to LinkedIn + Google Business profile"), and effort (minutes/hours/days).

## Output

```
DIAGNOSIS: <domain> — <date>

YOUR 15 FASTEST FIXES (ranked)
1. <fix> — impact <n>/5, effort <n>/5 — why: <evidence> — how: <one line>
...

QUESTIONS PEOPLE ASK AI THAT YOU NEVER ANSWER
1. "<question>" — <monthly volume or PAA source> — suggested page/section: <where it should live>
...

HAND-OFF
Fixes 1-N are content/schema changes → run the fix skill.
Fixes N+1... need human/dev decisions: <list>
```

Save to `seo-reports/diagnosis-<date>.md`. The fix skill consumes it.

## Rules
- Never pad to 15. If only 11 fixes are real, ship 11 and say so.
- Impact scores must trace to a number in the upstream reports (impressions, position, citation gap), not gut feel.
