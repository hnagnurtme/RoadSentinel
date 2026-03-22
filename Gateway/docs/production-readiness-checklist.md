# Gateway Production Readiness Checklist

Use this checklist before deploying the Gateway in long-running environments.

## 1. Runtime Resilience

- [ ] WebSocket sender queue is bounded and drop policy is documented.
- [ ] Camera stream parser has a hard cap for in-memory buffering.
- [ ] Startup sequence handles partial failures and performs resource rollback.
- [ ] Shutdown path is idempotent and safe under repeated signals.
- [ ] Retries use fixed or exponential backoff with reasonable max delay.

## 2. Configuration Safety

- [ ] All critical config fields are validated on startup.
- [ ] FPS, thresholds, queue sizes, and dimensions are constrained to valid ranges.
- [ ] Environment-specific config (dev/staging/prod) is separated.
- [ ] Device IDs and endpoint URLs are not hardcoded for production fleets.

## 3. Observability

- [ ] Logs include startup config summary (without secrets).
- [ ] Error logs contain enough context to debug capture/inference/sender failures.
- [ ] Log rotation and retention policy is defined and monitored.
- [ ] Health endpoint (or equivalent heartbeat) is available.

## 4. Performance and Capacity

- [ ] Target FPS is validated against hardware budget.
- [ ] End-to-end latency is measured (capture -> classify -> send).
- [ ] CPU and memory stay stable in soak tests (>= 8-24 hours).
- [ ] Overload behavior is defined (drop oldest, drop newest, or block).

## 5. Testing and Quality Gates

- [ ] Unit tests cover event classification priorities and state transitions.
- [ ] Unit tests cover config validation and invalid input handling.
- [ ] Integration test verifies sender reconnect and queue drain behavior.
- [ ] CI runs tests and static checks on every PR.

## 6. Security and Ops

- [ ] TLS/WSS is enabled outside local development.
- [ ] Sensitive endpoints and credentials are injected via environment variables.
- [ ] Dependency versions are pinned and periodically patched.
- [ ] Model file integrity/versioning is tracked.

## 7. Rollout Plan

- [ ] Deploy with canary devices first.
- [ ] Define rollback criteria (error rate, latency, memory growth).
- [ ] Alert thresholds are configured for disconnect rate and send failures.
- [ ] Keep a runbook for incident response and on-call handoff.
