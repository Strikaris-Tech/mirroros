# MirrorOS — Windows Setup Guide (Kevin)

Getting MirrorOS running on Windows for the hackathon demos. Everything here has been tested against the current `phase2-nova-demo` branch.

---

## What You Need

| Tool | Why |
|------|-----|
| Python 3.11+ | MRS bridge, demos, ledger |
| SWI-Prolog 9.x | The Prolog gate — required, not optional |
| Git | Clone the repo |
| Nova Act API key | Browser automation |
| AWS credentials | Nova Vision (Bedrock) — only needed for `--live` flag |

---

## Step 1 — Python

If you don't already have Python 3.11+:

1. Download from [python.org/downloads](https://www.python.org/downloads/) — get the Windows installer
2. During install, **check "Add Python to PATH"**
3. Verify: open PowerShell and run `python --version`

> Miniconda also works fine if you prefer. Brandon uses it.

---

## Step 2 — SWI-Prolog

This is the critical one. The MRS bridge calls SWI-Prolog at runtime — if it's not on PATH, nothing works.

1. Download the Windows installer from [swi-prolog.org/download/stable](https://www.swi-prolog.org/download/stable)
2. Run the installer — use defaults
3. **During install, check "Add SWI-Prolog to system PATH"**
4. Verify: open a new PowerShell window and run `swipl --version`

If `swipl` isn't found after install, add it manually:
- Default install path: `C:\Program Files\swipl\bin`
- Add that to your system PATH: Start → "Edit the system environment variables" → Environment Variables → Path → New

---

## Step 3 — Clone the Repo

```powershell
git clone https://github.com/Strikaris-Tech/mirroros-core.git
cd mirroros-core
git checkout phase2-nova-demo
```

---

## Step 4 — Install Python Dependencies

```powershell
pip install -r forge/requirements.txt
pip install z3-solver reportlab nova-act boto3
```

If you get a `z3-solver` build error, try:
```powershell
pip install z3-solver --prefer-binary
```

---

## Step 5 — Nova Act API Key

Get your key from [nova.amazon.com/act](https://nova.amazon.com/act).

```powershell
$env:NOVA_ACT_API_KEY = "your-key-here"
```

To make it permanent, add it to your user environment variables (Start → "Edit environment variables for your account").

---

## Step 6 — AWS Credentials (for Nova Vision)

Only needed if you're running demos with the `--live` flag (real Bedrock PDF extraction). For everything else, mock mode works without AWS.

```powershell
$env:AWS_ACCESS_KEY_ID = "..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_DEFAULT_REGION = "us-east-1"
```

Ask Brandon for the `mirroros-bedrock-dev` credentials if you don't have them. Note: Bedrock invocation is currently pending AWS account unblock — mock mode works fully in the meantime.

---

## Step 7 — Verify the Setup

Run the terminal-only demo (no browser, no API keys needed):

```powershell
python examples/ledgerlark_demo/ap_demo.py --no-browser
```

You should see 4 expenses processed with PERMITTED/REJECTED verdicts and `z3_verdict: VALID` in the reasoning log. If you see errors:

- `SWI-Prolog not found` → Step 2 PATH issue
- `ModuleNotFoundError` → re-run Step 4
- `z3_verdict: SKIP` → z3-solver not installed, re-run Step 4

---

## Step 8 — Run With Nova Act

Nova Act on Windows uses Chromium. It will download and manage its own browser — you don't need to install anything extra.

```powershell
$env:NOVA_ACT_API_KEY = "your-key"
python examples/ledgerlark_demo/ap_demo.py
```

> Note: On Windows the demo launches Nova Act's default browser rather than ungoogled-chromium (which is the macOS setup). The CDP profile trick Brandon uses is Mac-specific — on Windows Nova Act manages the browser directly. Zoho login will be prompted on first run; credentials are saved to Nova Act's profile.

---

## Running All Three Demos

### LedgerLark AP Orchestration
```powershell
python examples/ledgerlark_demo/ap_demo.py
```

### Zoho Quote-to-Cash
```powershell
python examples/zoho_demo/quote_demo.py                  # mock Nova Vision
python examples/zoho_demo/quote_demo.py --live           # real Nova Vision (needs AWS)
python examples/zoho_demo/quote_demo.py --seed 99        # exception path demo
```

### Invoice Approval (original demo)
```powershell
# Terminal 1
python examples/accounting_demo/server.py

# Terminal 2
python examples/accounting_demo/nova_demo.py
```

---

## Zoho Books Access

You'll need to log into the Strikaris Zoho Books account (`916562298`) the first time Nova Act opens it. Ask Brandon for login credentials. Once logged in, Nova Act's session is saved and you won't be prompted again.

---

## Troubleshooting

**`pyswip.prolog.PrologInitialisationError`**
SWI-Prolog is not on PATH. See Step 2.

**`ImportError: No module named 'nova_act'`**
Run `pip install nova-act`.

**`ValidationException: Operation not allowed` (Bedrock)**
Known issue — AWS account-level restriction being resolved with AWS Support. Use mock mode (`--no-browser` or without `--live`) for all demos in the meantime.

**Prolog gate returns no results / bridge hangs**
SWI-Prolog version mismatch. Confirm `swipl --version` shows 9.x. Version 8.x has known compatibility issues with pyswip on Windows.

**`z3_verdict: SKIP` instead of VALID**
z3-solver import is failing. Run `python -c "from z3 import Solver; print('ok')"` to confirm. If it fails, reinstall: `pip install z3-solver --force-reinstall`.

---

## Kevin's Open Items

These are the tasks from the original Phase 2 plan that are yours:

- [ ] **Nova Act scope** — validate the AP demo runs cleanly on your machine and the Zoho session persists
- [ ] **AWS workflow** — test the `--live` flag once Bedrock is unblocked; confirm Nova Pro extraction returns correct PO totals
- [ ] **Code review** — review `ledger/vision.py` and `mrs/bridge/mrs_bridge.py` for any issues before submission
- [ ] **AGPL sign-off** — confirm you've reviewed the license and are good with it for submission

---

## Branch Convention

```
main              ← stable, public-facing
phase2-nova-demo  ← current hackathon work (this branch)
```

All active work is on `phase2-nova-demo`. PRs should target `main` after Brandon reviews.

---

## Questions

Ping Brandon on Discord or drop a comment in the repo. Hackathon deadline: **March 16, 2026 @ 5pm PDT**.
