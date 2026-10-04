---
name: stock-analyst
description: >
  Analyze a stock's fundamentals and Reddit sentiment. Use when the user asks to analyse,
  evaluate, or research a stock or ticker (e.g. "analyse AAPL", "what do you think of TSLA",
  "fundamentals of MSFT", "is IONQ a good buy", "check sentiment on NVDA"). Fetches financial
  data from Yahoo Finance, scans Reddit for community sentiment, and produces a rated
  fundamentals table plus sentiment summary with sources.
---

# Stock Analyst

Analyze a given stock by (1) pulling fundamentals from Yahoo Finance and (2) scanning Reddit for sentiment, then produce a single summary with a rated fundamentals table and sentiment overview.

## Workflow

### Step 1: Identify the Ticker

Extract the ticker symbol from the user's request. If ambiguous, ask for clarification.

### Step 2: Fetch Fundamentals from Yahoo Finance

Navigate to `https://finance.yahoo.com/quote/{TICKER}` and capture:

**From the Statistics/Key Statistics page:**
- Forward P/E, Trailing P/E
- Price/Book (P/B)
- EV/EBITDA
- PEG Ratio
- Debt/Equity
- Current Ratio
- Interest Coverage (EBIT ÷ Interest Expense)
- Return on Equity (ROE)
- Return on Invested Capital (ROIC)
- Revenue growth (YoY)
- Net income margin
- Operating margin
- Free cash flow
- Shares outstanding (check for dilution trend — compare to 1 year ago)
- Insider transactions (recent buys/sells)
- Any one-time adjustments or non-recurring items in recent earnings

Also check the financials tab for:
- Revenue trend (last 4 quarters + annual — look for 5-10 year consistency)
- Net income trend
- FCF trend
- Earnings quality: compare FCF to net income (FCF/Net Income ratio)
- Debt trend (is it rising or falling?)

Use `web_fetch` on Yahoo Finance URLs or `browser` tool if web_fetch is blocked.

### Step 3: Rate Each Metric

Read `references/rating-model.md` for the rating thresholds. For each metric:
- Compare to the sector's typical range (not absolute thresholds)
- Assign a rating: 🟢 Good, 🟡 OK, 🔴 Poor
- For red flags, use ✅ Clear or 🚩 Flag

### Step 4: Scan Reddit for Sentiment

Search Reddit using `web_search` with queries like:
- `site:reddit.com {TICKER} stock`
- `site:reddit.com {COMPANY_NAME} analysis`
- `site:reddit.com {TICKER} bullish OR bearish`

Capture:
- Overall sentiment (bullish/bearish/mixed)
- Key bull arguments
- Key bear arguments
- Notable concerns or red flags mentioned
- Source URLs (keep 5-8 best threads)

### Step 5: Produce Output

Format the output as follows:

```
📊 {COMPANY_NAME} ({TICKER}) — Stock Analysis

--- FUNDAMENTALS ---
```

Present a table:

| Category | Metric | Value | Rating | Note |
|----------|--------|-------|--------|------|
| 💰 Profitability | Revenue Growth (YoY) | X% | 🟢/🟡/🔴 | Trend over 5yr |
| 💰 Profitability | Net Income Margin | X% | ... | Vs industry |
| 💰 Profitability | Operating Margin | X% | ... | Core business efficiency |
| 💰 Profitability | Free Cash Flow | $X | ... | The king — cash is real |
| 📊 Valuation | P/E (Forward) | Xx | ... | Vs industry |
| 📊 Valuation | P/B | Xx | ... | <1 = below book value |
| 📊 Valuation | EV/EBITDA | Xx | ... | Debt-adjusted |
| 📊 Valuation | PEG | Xx | ... | Growth-adjusted value |
| 🏦 Balance Sheet | Debt/Equity | Xx | ... | Lower = safer |
| 🏦 Balance Sheet | Current Ratio | Xx | ... | Can pay short-term bills? |
| 🏦 Balance Sheet | Interest Coverage | Xx | ... | Can service debt? |
| 📈 Quality | ROE | X% | ... | Capital allocation |
| 📈 Quality | ROIC | X% | ... | Value creation vs destruction |
| 📈 Quality | Earnings Quality (FCF/NI) | X% | ... | Real cash vs accounting |

Then the Red Flags section:
```
🚩 RED FLAGS
- Revenue ↑ but FCF ↓: ✅ Clear / 🚩 Flag — (detail)
- Rising debt + falling margins: ✅ Clear / 🚩 Flag — (detail)
- One-time adjustments: ✅ Clear / 🚩 Flag — (detail)
- Insider selling: ✅ Clear / 🚩 Flag — (detail)
- Dilution (rising share count): ✅ Clear / 🚩 Flag — (detail)
```

Then the overall score based on the rating model.

Then the sentiment section:
```
💬 REDDIT SENTIMENT
Overall: Bullish / Bearish / Mixed

Bull case:
- Point 1
- Point 2

Bear case:
- Point 1
- Point 2

Sources:
1. r/xxx — "Thread title" — URL
2. ...
```

### Step 6: Disclaimer

Always append: *"Not financial advice. Do your own research before investing."*

## Notes

- If Yahoo Finance data is unavailable or blocked, fall back to macrotrends.net or finviz
- For sector context, if unsure about industry benchmarks, note it explicitly
- Keep the analysis concise — tables over paragraphs
- If the user asks for a deeper dive on any specific metric, provide it
