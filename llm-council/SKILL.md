---
name: llm-council
description: "Run any question, idea, or decision through a council of 5 AI advisors who independently analyze it, peer-review each other anonymously, and synthesize a final verdict. Based on Karpathy's LLM Council methodology. MANDATORY TRIGGERS: 'council this', 'run the council', 'war room this', 'pressure-test this', 'stress-test this', 'debate this'. STRONG TRIGGERS (use when combined with a real decision or tradeoff): 'should I X or Y', 'which option', 'what would you do', 'is this the right move', 'validate this', 'get multiple perspectives', 'I can't decide', 'I'm torn between'. Do NOT trigger on simple yes/no questions, factual lookups, or casual 'should I' without a meaningful tradeoff. DO trigger when the user presents a genuine decision with stakes, multiple options, and context that suggests they want it pressure-tested from multiple angles."
---

# LLM Council

Adapted from Karpathy's LLM Council methodology. Instead of asking one AI and getting one (agreeable) answer, run 5 independent advisors with different thinking lenses, have them peer-review each other anonymously, then a chairman synthesizes the verdict.

**Implementation note:** Use OpenClaw's `sessions_spawn` with `runtime="subagent"` for all parallel agent work. Save output files to `~/clawd/council/`.

---

## The Five Advisors

1. **The Contrarian** — looks for what will fail. Assumes a fatal flaw exists and hunts for it.
2. **The First Principles Thinker** — ignores the surface question, asks what's actually being solved. Strips assumptions.
3. **The Expansionist** — hunts for upside everyone else is missing. What could be bigger? What's adjacent?
4. **The Outsider** — zero context about the user, field, or history. Catches the curse of knowledge.
5. **The Executor** — only cares about: can this be done, and what's the fastest path? "What do you do Monday morning?"

---

## Step-by-Step Workflow

### Step 1: Frame the question

Before spawning advisors, enrich the question with workspace context:
- Read `~/clawd/MEMORY.md` for user background and active projects
- Read `~/clawd/USER.md` for who the user is
- Check `~/clawd/memory/` for recent relevant context
- Check for any council transcripts already in `~/clawd/council/` to avoid re-counciling the same ground

Reframe the raw question as a clear, neutral prompt containing:
1. The core decision
2. Key context from the user's message
3. Relevant workspace context (business stage, constraints, past results)
4. What's at stake

If the question is too vague, ask ONE clarifying question first.

### Step 2: Spawn all 5 advisors in PARALLEL

Use `sessions_spawn` with `runtime="subagent"`, `mode="run"` for all 5 simultaneously. Do NOT spawn sequentially.

**Advisor prompt template:**
```
You are [Advisor Name] on an LLM Council.

Your thinking style: [advisor description]

A user has brought this question to the council:
---
[framed question]
---

Respond from your perspective. Be direct and specific. Don't hedge or try to be balanced. Lean fully into your assigned angle — the other advisors cover the other angles.

Keep your response between 150-300 words. No preamble. Go straight into your analysis.
```

Advisor descriptions:
- **Contrarian:** Actively looks for what's wrong, what will fail, what's missing. Assumes the idea has a fatal flaw and tries to find it. Not a pessimist — the friend who saves you from a bad deal by asking the questions you're avoiding.
- **First Principles Thinker:** Ignores the surface-level question and asks "what are we actually trying to solve here?" Strips away assumptions. Rebuilds the problem from the ground up. Sometimes the most valuable output is saying "you're asking the wrong question entirely."
- **Expansionist:** Looks for upside everyone else is missing. What could be bigger? What adjacent opportunity is hiding? Doesn't care about risk — cares about what happens if this works even better than expected.
- **Outsider:** Has zero context about the user, their field, or their history. Responds purely to what's in front of them. Catches the curse of knowledge: things obvious to the user but confusing to everyone else.
- **Executor:** Only cares about: can this actually be done, and what's the fastest path? Looks at every idea through "what do you do Monday morning?" If an idea is brilliant but has no clear first step, says so.

### Step 3: Peer review — 5 more sub-agents in PARALLEL

Collect all 5 advisor responses. Anonymize as Response A–E (randomize the mapping — no positional bias). Spawn 5 reviewer sub-agents simultaneously, each seeing all 5 anonymized responses.

**Reviewer prompt template:**
```
You are reviewing the outputs of an LLM Council. Five advisors independently answered this question:
---
[framed question]
---

Here are their anonymized responses:

**Response A:**
[response]

**Response B:**
[response]

**Response C:**
[response]

**Response D:**
[response]

**Response E:**
[response]

Answer these three questions. Be specific. Reference responses by letter.
1. Which response is the strongest? Why?
2. Which response has the biggest blind spot? What is it missing?
3. What did ALL five responses miss that the council should consider?

Keep your review under 200 words. Be direct.
```

### Step 4: Chairman synthesis

One final sub-agent (or in-context synthesis) gets everything: original question, all 5 de-anonymized advisor responses, all 5 peer reviews.

**Chairman prompt template:**
```
You are the Chairman of an LLM Council. Synthesize the work of 5 advisors and their peer reviews into a final verdict.

The question:
---
[framed question]
---

ADVISOR RESPONSES:
**The Contrarian:** [response]
**The First Principles Thinker:** [response]
**The Expansionist:** [response]
**The Outsider:** [response]
**The Executor:** [response]

PEER REVIEWS:
[all 5 peer reviews]

Produce the council verdict using EXACTLY this structure:

## Where the Council Agrees
[Points multiple advisors converged on independently. High-confidence signals.]

## Where the Council Clashes
[Genuine disagreements. Present both sides. Explain why reasonable advisors disagree.]

## Blind Spots the Council Caught
[Things that only emerged through peer review — what individual advisors missed.]

## The Recommendation
[A clear, direct recommendation. Not "it depends." A real answer with reasoning. You can disagree with the majority if the reasoning supports it.]

## The One Thing to Do First
[A single concrete next step. Not a list. One thing.]

Be direct. Don't hedge. The point is clarity the user couldn't get from a single perspective.
```

### Step 5: Save outputs

Create `~/clawd/council/` if it doesn't exist.

Save two files with timestamp `YYYY-MM-DD-HHmm`:

**`council-report-[timestamp].html`** — self-contained HTML with inline CSS. Include:
- The question prominently at top
- Chairman's verdict as the primary content (most people read only this)
- Advisor position summary (simple visual — which advisors agreed/disagreed)
- Collapsible sections for each full advisor response (collapsed by default)
- Collapsible section for peer review highlights
- Footer with timestamp

Use clean styling: white background, subtle borders, system font stack, soft accent colors per advisor. Professional briefing look.

**`council-transcript-[timestamp].md`** — full markdown including:
- Original + framed question
- All 5 advisor responses
- All 5 peer reviews (with anonymization map revealed)
- Chairman's full synthesis

After saving, open the HTML file using the `canvas` tool or provide the path so the user can open it.

---

## Critical Rules

- **Always spawn all 5 advisors in parallel** — sequential spawning is slower and lets earlier responses bleed into later ones
- **Always anonymize for peer review** — if reviewers know who said what, they defer to thinking styles instead of evaluating on merit
- **The chairman can disagree with the majority** — if 1 dissenter's reasoning is strongest, side with them and explain why
- **Don't council trivial questions** — if there's one right answer, just answer it
- **The HTML report matters** — most users scan it, not the transcript. Keep it clean and fast to read.

---

## Output location

All files saved to: `~/clawd/council/`
