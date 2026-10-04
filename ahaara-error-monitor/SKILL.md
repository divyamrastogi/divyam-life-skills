# Ahaara Error Monitor Skill

Proactive error monitoring pipeline for the Ahaara Flutter app.

## Flow

```
PostHog app_error events
        ↓
  Poll every hour via REST API
        ↓
  Deduplicate + group by (error_type, context)
        ↓
  Classify: simple vs complex
        ↓
  Simple → auto-fix → test → push
  Complex → analyze tradeoffs → message Divyam for choice
```

## PostHog Query

**Base URL:** https://eu.posthog.com  
**Project ID:** stored in ~/clawd/skills/ahaara-error-monitor/config.json  
**Personal API Key:** stored in ~/clawd/skills/ahaara-error-monitor/config.json  

Query endpoint: `POST /api/projects/{project_id}/query/`  
Auth: `Authorization: Bearer {personal_api_key}`

HogQL query to fetch recent errors (last N hours):
```sql
SELECT
  properties.error_type,
  properties.error_message,
  properties.context,
  properties.stack_trace,
  properties.is_flutter_error,
  count() as occurrences,
  max(timestamp) as last_seen,
  min(timestamp) as first_seen
FROM events
WHERE event = 'app_error'
  AND timestamp > now() - INTERVAL {hours} HOUR
GROUP BY
  properties.error_type,
  properties.error_message,
  properties.context,
  properties.stack_trace,
  properties.is_flutter_error
ORDER BY occurrences DESC
```

## State File

`~/clawd/skills/ahaara-error-monitor/state.json` tracks seen errors:
```json
{
  "lastChecked": "<ISO timestamp>",
  "seenErrors": {
    "<error_fingerprint>": {
      "firstSeen": "<ISO>",
      "lastSeen": "<ISO>",
      "occurrences": 42,
      "status": "reported|fixing|fixed|monitoring",
      "fixCommit": "abc123"
    }
  }
}
```

Error fingerprint = `sha256(error_type + "::" + context + "::" + first_100_chars_of_stack)`

## Complexity Classification

**Simple (auto-fix):**
- Single file change identifiable from stack trace
- Clear RCA (e.g. null check, wrong API call, missing try/catch)
- Existing test patterns in the codebase apply
- No DB migrations, no architectural changes
- Stack trace points to a specific line in Ahaara source (not a library)

**Complex (propose options):**
- Multiple files need changing
- Architectural decision required
- Root cause is ambiguous / multiple hypotheses
- Involves DB schema, Supabase RLS, or third-party library bugs
- Security or data-loss risk

## Auto-Fix Protocol (Simple errors)

1. Read the relevant source files (from stack trace)
2. Write the fix
3. Add/update a test in `test/` that would have caught this bug
4. Run: `cd ~/projects/souschef && flutter test test/<new_test_file>`
5. If tests pass: commit + push → CI builds TestFlight automatically
6. Report to Divyam in "Ahaara Dev Bot" WhatsApp group

Commit message format:
```
fix(<context>): <short description>

Auto-fix from PostHog error monitor.
Error: <error_type> in <context>
Occurrences: <N> (first seen: <date>)

PostHog fingerprint: <fingerprint>
```

## Complex Fix Protocol

When an error is complex, message Divyam with:

```
🐛 *New error detected* in Ahaara

*Error:* <error_type>
*Where:* <context>
*Occurrences:* <N> (first seen <X> ago)
*Stack:* <relevant lines>

*RCA:* <analysis>

*Options:*

*Option A — <name>*
  What: <description>
  Effort: <S/M/L>
  Risk: <Low/Medium/High>
  Tradeoff: <pros/cons>

*Option B — <name>*
  What: <description>
  Effort: <S/M/L>
  Risk: <Low/Medium/High>
  Tradeoff: <pros/cons>

Which option should I implement? (or reply with your own approach)
```

## Silent Clean Runs

**If there are no new errors: do NOT send any message to the group chat.** Just update the state file and finish silently.

Only message "Ahaara Dev Bot" (120363425113122951@g.us) when:
- A new error is detected (auto-fix or complex proposal)
- An auto-fix was committed and pushed

## Codebase Context

- **Repo:** /Users/deeksharastogi/projects/souschef
- **Tests:** /Users/deeksharastogi/projects/souschef/test/
- **Analytics events:** lib/services/analytics/analytics_events.dart
- **Error context values:** 'share_recipe', 'async_zone', 'flutter_framework', 'cooking_mode', etc.
- **CI:** GitHub Actions (.github/workflows/deploy-testflight.yml), triggers on push to main
- **Group chat:** 120363425113122951@g.us (Ahaara Dev Bot)
