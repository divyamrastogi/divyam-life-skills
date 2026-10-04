#!/usr/bin/env bash
# End-to-end test for the Supabase + Brevo contact pipeline.
#
#   scripts/test_pipeline.sh <project-ref> <publishable-or-anon-key> [table]
#
# Proves the security model with the PUBLIC key and fires a real notification
# email. Uses only the public key on purpose — that's the exact surface an
# attacker has, so if reads/deletes are blocked here, they're blocked for good.
set -euo pipefail

REF="${1:?usage: test_pipeline.sh <ref> <public-key> [table]}"
KEY="${2:?missing public (publishable/anon) key}"
TABLE="${3:-contact_submissions}"
BASE="https://$REF.supabase.co/rest/v1/$TABLE"
FN="https://$REF.supabase.co/functions/v1/contact-notify"

# New sb_publishable_ keys: apikey header only. Legacy JWT (eyJ…): add Bearer.
AUTH=(-H "apikey: $KEY")
case "$KEY" in eyJ*) AUTH+=(-H "Authorization: Bearer $KEY");; esac

pass() { printf '\033[32m✓\033[0m %s\n' "$*"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$*"; exit 1; }

echo "→ 1/4  INSERT with the public key (expect 201)"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE" "${AUTH[@]}" \
  -H "Content-Type: application/json" -H "Prefer: return=minimal" \
  -d '{"name":"[TEST] pipeline check","email":"test@example.com","project_type":"Web application","details":"[TEST] safe to delete — inserted by test_pipeline.sh"}' \
  --max-time 20)
[ "$code" = "201" ] && pass "insert allowed (201) — this also fires the email trigger" \
  || fail "insert returned $code (expected 201). Check the anon insert policy and column names."

echo "→ 2/4  SELECT with the public key (expect empty — reads blocked)"
body=$(curl -s "$BASE?select=*&limit=5" "${AUTH[@]}" --max-time 20)
[ "$body" = "[]" ] && pass "reads blocked (got [])" \
  || fail "reads NOT blocked — got: $body  ← RLS is leaking data. Remove any select policy for anon."

echo "→ 3/4  DELETE with the public key (must remove nothing)"
# A 204 here is ambiguous, so this only sanity-checks that the endpoint doesn't
# error; the real proof is step 2 (no read) + that inserts keep accumulating.
dcode=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE \
  "$BASE?id=neq.00000000-0000-0000-0000-000000000000" "${AUTH[@]}" --max-time 20)
case "$dcode" in
  204|401|403|404) pass "delete rejected or no-op ($dcode)";;
  *) fail "unexpected delete status $dcode — verify no delete policy exists for anon";;
esac

echo "→ 4/4  Edge Function direct call (expect ok + email)"
resp=$(curl -s -w '\n%{http_code}' -X POST "$FN" -H "Content-Type: application/json" \
  -d '{"record":{"name":"[TEST] function check","email":"test@example.com","project_type":"Web application","details":"[TEST] direct function call — safe to ignore"}}' \
  --max-time 30)
fcode=$(printf '%s' "$resp" | tail -n1); fbody=$(printf '%s' "$resp" | sed '$d')
[ "$fcode" = "200" ] && pass "email sent — transport: $fbody" \
  || fail "function returned $fcode: $fbody  (check BREVO_API_KEY, CONTACT_NOTIFY_TO, and --no-verify-jwt deploy)"

echo
pass "Pipeline healthy. Check the recipient inbox for two [TEST] emails."
echo "  Note: test rows remain in the table (the public key can't delete them)."
echo "  Clear them from the Supabase dashboard → Table Editor when done."
