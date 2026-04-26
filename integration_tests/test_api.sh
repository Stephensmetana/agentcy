#!/usr/bin/env bash
# integration_tests/test_api.sh
#
# Integration tests for the Agentcy REST API.
# Requires the server to be running (Docker or local).
# Safe to run against a server with existing data -- tests use unique
# markers and check relative state, not absolute list lengths.
#
# Usage:
#   bash integration_tests/test_api.sh [BASE_URL]
#
# Defaults:
#   BASE_URL → http://localhost:9001
#
# Exit codes:
#   0 -- all tests passed
#   1 -- one or more tests failed

set -euo pipefail

DEV_SERVER_URL="http://localhost:9001"
BASE_URL="${1:-${DEV_SERVER_URL}}"
PASS=0
FAIL=0
# Unique run ID so our test data is identifiable even alongside existing data
RUN_ID="itest_$(date +%s)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

pass() { echo -e "  ${GREEN}PASS${RESET} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}FAIL${RESET} $1"; FAIL=$((FAIL + 1)); }
section() { echo -e "\n${CYAN}>> $1${RESET}"; }

get()  { curl -sf "${BASE_URL}${1}"; }
post() { curl -sf -X POST "${BASE_URL}${1}" -H "Content-Type: application/json" -d "${2}"; }

assert_contains() {
  if grep -qF "$2" <<< "$1"; then
    pass "$3"
  else
    fail "$3 (expected '$2' in: $(head -c 120 <<< "$1"))"
  fi
}

assert_not_contains() {
  if ! grep -qF "$2" <<< "$1"; then
    pass "$3"
  else
    fail "$3 (did NOT expect '$2' in response)"
  fi
}

assert_equals() {
  if [[ "$1" == "$2" ]]; then pass "$3"; else fail "$3 (expected '$2', got '$1')"; fi
}

# ---------------------------------------------------------------------------
# Wait for server
# ---------------------------------------------------------------------------
echo -e "${CYAN}Agentcy Integration Tests${RESET}"
echo "Target:  ${BASE_URL}"
echo "Run ID:  ${RUN_ID}"
echo -n "Waiting for server"
for i in $(seq 1 20); do
  if curl -sf "${BASE_URL}/api/messages" > /dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
  if [[ $i -eq 20 ]]; then
    echo ""
    echo -e "${RED}ERROR: server not reachable at ${BASE_URL} after 20s${RESET}"
    exit 1
  fi
done

# ---------------------------------------------------------------------------
section "GET /api/messages -- response shape"
RESP=$(get "/api/messages")
if echo "$RESP" | python3 -c "import sys,json; data=json.load(sys.stdin); assert isinstance(data, list)" 2>/dev/null; then
  pass "returns a JSON array"
else
  fail "response is not a JSON array"
fi

# ---------------------------------------------------------------------------
section "GET /api/latest -- response shape"
RESP=$(get "/api/latest")
if echo "$RESP" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  pass "returns valid JSON"
else
  fail "response is not valid JSON"
fi

# ---------------------------------------------------------------------------
section "GET /api/agents -- response shape"
RESP=$(get "/api/agents")
if echo "$RESP" | python3 -c "import sys,json; data=json.load(sys.stdin); assert isinstance(data, list)" 2>/dev/null; then
  pass "returns a JSON array"
else
  fail "response is not a JSON array"
fi

# ---------------------------------------------------------------------------
section "GET /api/channels -- general channel exists"
RESP=$(get "/api/channels")
assert_contains "$RESP" '"general"' "general channel seeded on init"
if echo "$RESP" | python3 -c "import sys,json; data=json.load(sys.stdin); assert isinstance(data, list) and len(data)>=1" 2>/dev/null; then
  pass "channels list has at least one entry"
else
  fail "channels list is empty or not an array"
fi

# ---------------------------------------------------------------------------
section "POST /api/messages -- round trip"
MARKER="${RUN_ID}_round_trip"
POST_RESP=$(post "/api/messages" "{\"content\":\"${MARKER}\",\"channel\":\"general\"}")

assert_contains "$POST_RESP" "${MARKER}" "POST returns our message content"
assert_contains "$POST_RESP" '"sender":"user"' "POST sets sender to user"
assert_contains "$POST_RESP" '"channel":"general"' "POST stores channel field"
assert_contains "$POST_RESP" '"id"' "POST returns an id"
assert_contains "$POST_RESP" '"timestamp"' "POST returns a timestamp"

MSG_ID=$(echo "$POST_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
if [[ -n "$MSG_ID" && "$MSG_ID" =~ ^[0-9]+$ ]]; then
  pass "id is a positive integer ($MSG_ID)"
else
  fail "could not extract numeric id from POST response"
fi

# ---------------------------------------------------------------------------
section "GET /api/messages -- our message appears in list"
ALL=$(get "/api/messages?channel=general")
assert_contains "$ALL" "${MARKER}" "our message is in GET /api/messages"

# ---------------------------------------------------------------------------
section "GET /api/latest -- reflects most recent message"
LATEST_MARKER="${RUN_ID}_latest"
post "/api/messages" "{\"content\":\"${LATEST_MARKER}\",\"channel\":\"general\"}" > /dev/null

LATEST=$(get "/api/latest?channel=general")
assert_contains "$LATEST" "${LATEST_MARKER}" "latest returns the most recently posted message"

# ---------------------------------------------------------------------------
section "GET /api/messages/since/{id} -- pagination"
AFTER_MARKER="${RUN_ID}_after"
LAST_MARKER="${RUN_ID}_last"
post "/api/messages" "{\"content\":\"${AFTER_MARKER}\",\"channel\":\"general\"}" > /dev/null
post "/api/messages" "{\"content\":\"${LAST_MARKER}\",\"channel\":\"general\"}" > /dev/null

SINCE=$(get "/api/messages/since/${MSG_ID}?channel=general")
assert_contains "$SINCE" "${AFTER_MARKER}" "since returns messages posted after anchor id"
assert_contains "$SINCE" "${LAST_MARKER}" "since returns all messages after anchor"
assert_not_contains "$SINCE" "${MARKER}" "since excludes the anchor message itself"

# ---------------------------------------------------------------------------
section "Channel isolation"
DESIGN_MARKER="${RUN_ID}_design"
post "/api/messages" "{\"content\":\"${DESIGN_MARKER}\",\"channel\":\"design\"}" > /dev/null

GENERAL=$(get "/api/messages?channel=general")
DESIGN=$(get "/api/messages?channel=design")

assert_not_contains "$GENERAL" "${DESIGN_MARKER}" "design message is NOT in general channel"
assert_contains     "$DESIGN"  "${DESIGN_MARKER}" "design message IS in design channel"
assert_not_contains "$DESIGN"  "${MARKER}"        "general message does NOT leak into design"

# ---------------------------------------------------------------------------
section "GET /api/latest scoped to channel"
LATEST_DESIGN=$(get "/api/latest?channel=design")
assert_contains     "$LATEST_DESIGN" "${DESIGN_MARKER}"  "latest in design is our design message"
assert_not_contains "$LATEST_DESIGN" "${LATEST_MARKER}"  "general message does not appear as latest in design"

# ---------------------------------------------------------------------------
section "POST /api/messages -- input validation"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/messages" \
  -H "Content-Type: application/json" -d '{"content":""}')
assert_equals "$HTTP_STATUS" "400" "empty content -> 400"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/messages" \
  -H "Content-Type: application/json" -d '{}')
assert_equals "$HTTP_STATUS" "400" "missing content field -> 400"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/messages" \
  -H "Content-Type: application/json" -d '{"content":"   "}')
assert_equals "$HTTP_STATUS" "400" "whitespace-only content -> 400"

# ---------------------------------------------------------------------------
section "GET / -- browser UI served"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/")
assert_equals "$HTTP_STATUS" "200" "GET / returns 200"
UI_BODY=$(curl -sf "${BASE_URL}/")
assert_contains "$UI_BODY" "<html" "response body is HTML"

# ---------------------------------------------------------------------------
# Summary
echo ""
echo "------------------------------------"
TOTAL=$((PASS + FAIL))
echo -e "Results: ${GREEN}${PASS} passed${RESET}, ${RED}${FAIL} failed${RESET} (${TOTAL} total)"
echo "------------------------------------"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
