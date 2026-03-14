# MirrorOS — Windows Setup Guide (Kevin)

Getting MirrorOS running on Windows for the hackathon demos. Everything here has been tested against the current `phase2-nova-demo` branch.

---

## What You Need

| Tool | Why |
|------|-----|
| Docker Desktop | Runs Python, SWI-Prolog, and MRS inside a container — no local install needed |
| Git | Clone the repo |
| Nova Act API key | Browser automation (only for demos with `--live` or full Nova Act) |
| AWS credentials | Nova Vision (Bedrock) — only needed for `--live` flag |

Python and SWI-Prolog do **not** need to be installed locally. They run inside Docker.

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

## Step 4 — Install Nova Act (host only)

Python, SWI-Prolog, and all other deps run inside Docker. The only thing you need locally is Nova Act, and only for browser automation demos:

```powershell
pip install nova-act boto3
```

---

## Step 4b — Docker (optional, for ledger sealing)

Docker is only needed if you want immudb running locally so the demo seals verdicts to the tamper-proof ledger. The demo runs fine without it — it falls back to JSON-only logging.

If you want immudb:

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. From the repo root:

```powershell
docker compose up -d immudb
```

immudb will be available at `localhost:3324` (port intentionally offset from 3322 to avoid conflicts with other MirrorOS instances).

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

Start the services:
```powershell
docker compose up -d
```

Run the terminal-only AP demo inside the container (no API keys needed):
```powershell
docker compose exec forge python examples/ledgerlark_demo/ap_demo.py --no-browser
```

You should see 4 expenses processed with PERMITTED/REJECTED verdicts.

For the raw governance pulse demo (5 pulses, Docker only):
```powershell
# Requires Git Bash or WSL — quickstart.sh is a bash script
bash quickstart.sh
```

If you see errors:

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

> Note: On Windows, Nova Act manages its own browser automatically — you don't need Chromium installed. The demo detects whether ungoogled-chromium is present; if not, it hands control to Nova Act's built-in browser. Zoho login will be prompted on first run; credentials are saved to Nova Act's profile.

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

### LedgerLark Invoice UI (browser, no Zoho account needed)
```powershell
docker compose exec forge python examples/accounting_demo/server.py
```
Then open **http://localhost:7242** in your browser. Click approve/reject manually, or run Nova Act automation from the host:
```powershell
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
