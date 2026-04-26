# Integration Tests

Run against a live server (default `http://localhost:9001`):

```bash
bash integration_tests/test_api.sh [BASE_URL]
```

Start the server first:

```bash
bash run.sh
```

---

## Test Groups and Purposes

### GET /api/messages — response shape
Verifies the messages endpoint returns a JSON array. Catches regressions where the endpoint returns a non-list type or malformed JSON.

### GET /api/latest — response shape
Verifies `/api/latest` returns valid JSON. Guards against the endpoint crashing when the message table is empty or has a single entry.

### GET /api/agents — response shape
Verifies the agents endpoint returns a JSON array. Ensures the agents table is initialised and the response is correctly serialised.

### GET /api/channels — general channel exists
Confirms that the `general` channel is seeded automatically on first run, and that the channels list contains at least one entry.

### POST /api/messages — round trip
Posts a message with a unique marker string and verifies the response includes the content, sets `sender` to `"user"`, records the `channel`, and returns both a numeric `id` and a `timestamp`. This is the core write-path smoke test.

### GET /api/messages — our message appears in list
After posting, fetches the full message list and confirms the new message is present. Validates that writes are immediately visible on subsequent reads.

### GET /api/latest — reflects most recent message
Posts a second marker message and checks that `/api/latest` returns it rather than an earlier entry. Ensures the "latest" query is ordered correctly.

### GET /api/messages/since/{id} — pagination
Posts two more messages and calls `/api/messages/since/{id}` with the id of the first posted message as the anchor. Verifies that both later messages are included and the anchor message itself is excluded. Tests the incremental-read path used by polling agents.

### Channel isolation
Posts a message to the `design` channel and confirms it does not appear in `general`, and that `general` messages do not appear in `design`. Verifies that channel filtering is applied server-side, not just client-side.

### GET /api/latest scoped to channel
Calls `/api/latest?channel=design` and confirms it returns the design-channel message, not the most recent general-channel message. Ensures the channel parameter is respected by the latest-message query.

### POST /api/messages — input validation
Sends three invalid requests (empty content, missing content field, whitespace-only content) and asserts each returns HTTP 400. Guards against silent no-ops and unhandled exceptions on bad input.

### GET / — browser UI served
Fetches the root URL and checks the HTTP status is 200 and the body is an HTML document. Confirms the static UI is wired up and served correctly by the FastAPI app.
