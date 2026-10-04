# Trump Trade Alert

Monitors Trump's public statements, executive orders, and policy moves for market impact. Identifies affected stocks/sectors and sends actionable alerts.

## Trigger
- Cron job runs every 2 hours during US market hours (14:00-22:00 UK / 09:00-17:00 ET)
- Also runs once in the morning (07:00 UK) for pre-market moves
- Can be triggered manually with "run trump trade check"

## What It Tracks
1. **Truth Social posts** — via news coverage (can't scrape directly)
2. **Executive orders** — Federal Register + news
3. **Tariff/trade announcements** — specific countries/sectors
4. **Crypto moves** — World Liberty Financial on-chain activity
5. **Regulatory actions** — FDA, FTC, SEC moves tied to Trump policy

## Alert Format
Each alert includes:
- What was said/done (with source)
- Sectors/tickers affected (bullish 🟢 and bearish 🔴)
- Suggested action (watch, buy dip, take profits)
- Time sensitivity (trade now, this week, background)

## Output
- Sends to Trader Bot WhatsApp group (120363411953543280@g.us)
- Keeps alerts concise — max 5-6 lines
- Only sends when there's genuinely new, actionable info (no filler)

## Known Tickers to Watch
- **DJT** — Trump Media (direct proxy)
- **Crypto**: BTC, ETH, WLFI tokens
- **Defense**: LMT, RTX, NOC, GD
- **Oil/Gas**: XOM, CVX, COP, SLB
- **Pharma**: JNJ, PFE, LLY, MRK
- **Tech/Tariff-vulnerable**: AAPL, TSLA, NVDA, semis (SMH)
- **Steel/Aluminum**: NUE, STLD, AA, X
- **China-exposed**: BABA, JD, PDD, FXI

## Rules
- Only alert on NEW info (check last alert timestamp)
- No speculation — only flag what's been publicly stated
- If market already moved >5%, note it's too late for that particular trade
- Weekend/late night → batch into morning summary, don't send individually
