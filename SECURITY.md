# Security Policy

## Threat Model

MirrorOS is a governance layer — it gates agent actions, not a network perimeter. The relevant threat surface:

| Threat | Mitigation |
|--------|-----------|
| Agent bypasses MRS gate | All actions must pass `MRSBridge.check_authorization()` — never call backend directly |
| Malicious Prolog assertion | `assert_fact()` validates against Codex before asserting — contradictions are rejected |
| Tampered audit trail | immudb `verifiedSet` — every write returns a cryptographic proof; `result.verified == True` |
| Leaked API keys | Keys are loaded from environment variables only — never committed to the repo |
| Concordance drift (Z3 ↔ Prolog desync) | Boot check in `MRSBridge._verify_concordance_coverage()` raises `ConcordanceError` on mismatch |

## What Is Not in This Repo

The following are intentionally absent from the public codebase:
- Production immudb keys or connection strings
- Any client-specific compliance rules
- Agent configurations for production deployments
- `.env` files of any kind

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Report to: **security@mirroros.dev** (or substitute your contact address here before publishing)

Include:
- A description of the vulnerability
- Steps to reproduce
- Your assessment of impact

You will receive a response within 72 hours. We will coordinate a fix and disclosure timeline with you.

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch | Yes |
| Tagged releases | Current release only |
