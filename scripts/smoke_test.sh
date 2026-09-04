#!/usr/bin/env bash
# End-to-end smoke test against a running backend (default http://localhost:8000).
# Usage: scripts/smoke_test.sh [BASE_URL]
set -euo pipefail
BASE="${1:-http://localhost:8000}"

echo "== health =="
curl -fsS "$BASE/api/health" | head -c 200; echo

echo "== login =="
TOKEN=$(curl -fsS -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"demo1234"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
AUTH="Authorization: Bearer $TOKEN"

echo "== companies =="
COMPANY=$(curl -fsS "$BASE/api/companies" -H "$AUTH" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d[0]["id"] if d else "")')
[ -n "$COMPANY" ] || { echo "no companies — run python -m app.seed"; exit 1; }
echo "company: $COMPANY"

echo "== overview (scorecards) =="
curl -fsS "$BASE/api/companies/$COMPANY/overview" -H "$AUTH" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print({s["label"]: s["score"] for s in d["scorecards"]})'

echo "== risks / opportunities / inconsistencies =="
curl -fsS "$BASE/api/companies/$COMPANY/risks" -H "$AUTH" | python3 -c 'import sys,json;print("risks:",len(json.load(sys.stdin)))'
curl -fsS "$BASE/api/companies/$COMPANY/opportunities" -H "$AUTH" | python3 -c 'import sys,json;print("opportunities:",len(json.load(sys.stdin)))'
curl -fsS "$BASE/api/companies/$COMPANY/inconsistencies" -H "$AUTH" | python3 -c 'import sys,json;print("inconsistencies:",len(json.load(sys.stdin)))'

echo "== chat =="
curl -fsS -X POST "$BASE/api/companies/$COMPANY/chat" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"question":"What was revenue in FY2025?"}' \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("answer:",d["answer"][:120]);print("citations:",[(c["document_name"],c["page_number"]) for c in d["citations"]])'

echo "== report =="
REPORT=$(curl -fsS "$BASE/api/companies/$COMPANY/reports" -H "$AUTH" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d[0]["id"] if d else "")')
[ -n "$REPORT" ] && curl -fsS "$BASE/api/reports/$REPORT" -H "$AUTH" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("report sections:",len(d.get("content",{})))'

echo "SMOKE TEST PASSED"
