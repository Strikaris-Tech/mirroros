# MirrorOS Phase 2 — Code Review
**Reviewer:** Kevin Khan
**Branch:** `phase2-nova-demo`
**Date:** 2026-03-10

---

## `mrs/bridge/mrs_bridge.py`

**Overall: ✅ Approved with minor notes**

### Bug Fixes Applied (Windows compatibility)
The following issues were found and fixed during Windows testing:

- **Backslash path errors** — `str(path)` was being passed directly to Prolog's `consult/1`, causing `Illegal \U or \u sequence` errors on Windows paths. Fixed by replacing all instances with `Path(x).as_posix()` across `_load_prolog_files`, `_load_concordance`, and `load_module`.
- **Wrong variable reference in `_load_prolog_files`** — `concordance_path` was referenced in scope where only `codex_laws` and `agent_rules` exist. Corrected to use the right variable.
- **Malformed consult call in `load_module`** — Leftover debris from a prior edit produced an unterminated string literal. Replaced with clean two-line pattern.

All fixes committed to `phase2-nova-demo`.

### Observations (Non-blocking)

- **`essence_runes.py` missing from branch** — `mrs/verifier/essence_runes.py` is not present in the repo. The bridge handles this gracefully via try/except, but all Z3 verdicts log as `"error": "No module named 'mrs.verifier.essence_runes'"`. Is this file coming or is Z3 out of scope for submission?
- **Logic is solid** — Dual-gate flow (Prolog → Z3), concordance boot check, ledger sealing, and reasoning log structure are all clean and well-documented.
- **Windows path handling now consistent** — All `consult()` calls use `.as_posix()`. Recommend applying same pattern to any future path handling in the file.

---

## `ledger/vision.py`

**Overall: ✅ Approved with minor notes**

### Observations (Non-blocking)

- **Hardcoded date in mock** — `_mock_from_po_data` returns `"date": "2026-03-04"` as a fixed string. Should use `datetime.now().strftime("%Y-%m-%d")` so it doesn't look stale in demos.
- **Unclosed file handle** — `_call_nova_pro` uses `open(pdf_path, "rb").read()` without a context manager. Should be:
  ```python
  with open(pdf_path, "rb") as f:
      pdf_bytes = f.read()
  ```
- **`MOCK_VISION = True` flag** — Fine for the hackathon. Worth a comment noting it should flip to `False` once the AWS Bedrock account restriction is resolved.
- **Everything else is clean** — Extraction prompt is clear, mock/real separation is well-structured, return shape is consistent, error handling is documented.

---

## Demo Run — LedgerLark AP (`--no-browser`)

✅ Demo ran successfully on Windows (MSYS2) after path fixes.
All 4 expenses processed with correct PERMITTED/REJECTED verdicts.
Reasoning log writing to `mrs/memory/reasoning_log.json` confirmed.
Z3 verdicts showing `SKIP` (expected — `essence_runes.py` not present).

---

## Outstanding Items (Per Khan Guide)

| Task | Status |
|---|---|
| Validate AP demo runs on Windows | ✅ Done |
| Code review `ledger/vision.py` | ✅ Done |
| Code review `mrs/bridge/mrs_bridge.py` | ✅ Done |
| Test `--live` flag (Bedrock) | ⏳ Blocked — awaiting AWS account unblock |
| Apache 2.0 sign-off | ⏳ Pending |
