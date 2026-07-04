---
id: BACKLOG-008
type: backlog
status: open
source: issue #43 (2nd deploy report)
created: 2026-07-04
---

# BACKLOG-008: tls_emulation fetch fails non-blocking (issue #43 N3)

## What

telemt `tls_emulation` fetch to `www.microsoft.com:443` fails with `Connection reset by peer`.
Non-blocking — telemt falls back to built-in fake cert (`fake_cert_len=2048`). Proxy works.

## Possible cause

Xray-exit on `:443` in host network mode may interfere with telemt's outbound TLS fetch.
Needs investigation — telemt connects to external `www.microsoft.com:443`, not localhost.
May be Hetzner network-specific.

## Severity

Low. Proxy functional without tls_emulation. Investigate during next deploy cycle.
