---
name: visibility
description: Score a brand's AI search visibility out of 100 across ChatGPT, Gemini, Perplexity and Google AI Overviews using the DataForSEO MCP, and explain exactly why the brand is skipped. Use when asked "does AI recommend us", "check our AI visibility", or "run the visibility skill".
---

# Visibility

Answer the only question that matters in AI search: when a buyer asks an AI who to choose, does your brand come up — or your competitor?

## Inputs
- Brand name + domain (ask if not given).
- 3-5 "money questions" a buyer would ask (derive from the audit report's top queries if present, else generate from the site's services and confirm with the user).
- DataForSEO MCP connected.

## Steps

1. **Build the question set**: 5 buyer-intent questions, e.g. "best <category> in <city>", "who should I hire for <service>", "<product> vs alternatives". Conversational phrasing, the way people talk to a chatbot.
2. **Check Google AI Overviews** (DataForSEO SERP API): for each question, fetch the Google SERP and inspect the AI Overview block. Record: does an AI Overview appear, is the brand cited in it, which competitors are cited.
3. **Check LLM answers** (DataForSEO LLM/AI endpoints where available on your plan): query each question against the available AI answer endpoints and record brand mentions vs competitor mentions. Where an endpoint is not on the plan, run the question as a standard organic SERP and use top-10 presence as the proxy, and SAY it is a proxy.
4. **Check the brand query**: search the exact brand name. Is the site ranking #1 for itself, does a knowledge panel exist, do third-party pages (reviews, directories, LinkedIn) corroborate the brand? AI systems lean on corroboration — a brand that only exists on its own site gets skipped.
5. **Score it /100**:
   - 40 pts: brand cited in AI answers/Overviews for money questions (8 per question)
   - 25 pts: competitor citation gap (full points if you appear at least as often as the top competitor)
   - 20 pts: corroboration (third-party mentions, reviews, structured citations)
   - 15 pts: machine readability (llms.txt, schema, crawlable, AI bots not blocked — pull from the audit report)
6. **Explain the skips**: for every question where the brand was absent, name who showed up instead and the most likely reason (no answering content, no corroboration, blocked crawler, thin schema).

## Output

```
AI VISIBILITY: <brand> — <date>
SCORE: <n>/100

PER QUESTION
"<question>" — AI Overview: <cited/skipped> · LLM answers: <cited/skipped> · who shows instead: <names>

WHY YOU'RE SKIPPED
1. <reason> — <evidence>

SCORE BREAKDOWN: citations <n>/40 · competitor gap <n>/25 · corroboration <n>/20 · readability <n>/15
```

Save to `seo-reports/visibility-<date>.md`. The diagnose skill consumes it.

## Rules
- Real responses only. If an endpoint fails or is unavailable, mark that question "NOT CHECKED" — never simulate an AI answer.
- Always name the competitors that ARE being recommended. That line is what makes the report actionable (and shareable).
