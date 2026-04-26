# Agentcy — Claude Code Guidelines

## Testing Policy

### After every code change: run unit tests
Always run the unit test suite after making any change:

```bash
pytest tests/ -m "not integration and not e2e"
```

All unit tests must pass before considering a change complete.

### Integration tests: only when explicitly requested
Tests marked `integration` or `e2e` invoke the real Claude CLI or hit a live server. These are slow and consume API credits. **Do not run them automatically.** Only run them when the user explicitly asks for a detailed or full integration test run:

```bash
# Run integration tests (spawns real subprocesses, requires claude binary)
pytest tests/ -m integration

# Run e2e tests (requires live server at localhost:9001, calls Claude API)
pytest tests/ -m e2e

# Run everything
pytest tests/
```

The `pytest.ini` markers are:
- `integration` — tests that spawn real subprocesses (require `claude` binary)
- `e2e` — full end-to-end tests against a live server (slow, calls Claude API)
