# MirrorOS — Windows Setup Guide (Kevin)

Getting MirrorOS running on Windows for the hackathon demos. Everything here has been tested against the current `phase2-nova-demo` branch.

---

## What You Need

| Tool | Why |
|------|-----|
| Docker Desktop | Runs everything — Python, SWI-Prolog, MRS, immudb |
| Git | Clone the repo |
| Nova Act API key | Browser automation demos only |
| AWS credentials | `--live` flag only (Nova Vision / Bedrock) |

Python and SWI-Prolog do **not** need to be installed locally. They run inside Docker.

---

## Step 1 — Docker Desktop

Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/). Make sure it's running before continuing.

---

## Step 2 — Clone the Repo

```powershell
git clone https://github.com/Strikaris-Tech/mirroros-core.git
cd mirroros-core
git checkout phase2-nova-demo
```

---

## Step 3 — Verify the Setup

Clean start (removes any stale containers and volumes):

```powershell
docker compose down -v
bash quickstart.sh
```

> `quickstart.sh` is a bash script — requires Git Bash or WSL on Windows.

You should see:

```
PERMITTED  clerk      approve_payment      ($200 — within clerk limit)
REJECTED   clerk      approve_payment      (exceeds_clerk_limit)
REJECTED   clerk      pay_vendor           (unapproved_vendor)
PERMITTED  auditor    approve_payment      ($25k — within auditor limit)
PERMITTED  auditor    compliance_check
```

If that runs clean, the stack is working.

---

## Step 4 — Nova Act API Key

Only needed for browser automation demos.

Get your key from [nova.amazon.com/act](https://nova.amazon.com/act).

```powershell
$env:NOVA_ACT_API_KEY = "your-key-here"
```

To make it permanent: Start → "Edit environment variables for your account".

---

## Step 5 — AWS Credentials (for `--live` only)

Only needed for the Zoho Quote-to-Cash demo with real Bedrock PDF extraction. Mock mode works without it.

```powershell
$env:AWS_ACCESS_KEY_ID = "..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_DEFAULT_REGION = "us-east-1"
```

Ask Brandon for the `mirroros-bedrock-dev` credentials. Note: Bedrock is pending AWS account unblock — mock mode works fully in the meantime.

---

## Running the Demos

Services must be up first:
```powershell
docker compose up -d
```

### Governance Pulses (Docker only, no API key)
```powershell
bash quickstart.sh
```

### LedgerLark Invoice UI (Docker + browser, no Zoho account needed)
```powershell
docker compose exec forge python examples/accounting_demo/server.py
```
Open **http://localhost:7242**. Click approve/reject manually, or run Nova Act from the host:
```powershell
python examples/accounting_demo/nova_demo.py
```

### LedgerLark AP Orchestration — terminal only (Docker, no API key)
```powershell
docker compose exec forge python examples/ledgerlark_demo/ap_demo.py --no-browser
```

### LedgerLark AP Orchestration — with Nova Act (runs on host)
```powershell
$env:NOVA_ACT_API_KEY = "your-key"
python examples/ledgerlark_demo/ap_demo.py
```

> On Windows, Nova Act manages its own browser automatically — no Chromium install needed.

### Zoho Quote-to-Cash (runs on host)
```powershell
python examples/zoho_demo/quote_demo.py                  # mock Nova Vision
python examples/zoho_demo/quote_demo.py --live           # real Nova Vision (needs AWS)
python examples/zoho_demo/quote_demo.py --seed 99        # exception path
```

---

## Zoho Books Access

You'll need to log into the Strikaris Zoho Books account (`916562298`) the first time Nova Act opens it. Ask Brandon for credentials. Once logged in, Nova Act's session is saved.

---

## Troubleshooting

**Quickstart times out waiting for Forge**
Run `docker compose logs forge` to see what failed during startup.

**`ImportError: No module named 'nova_act'`**
Run `pip install nova-act`. This is the only pip install needed.

**`ValidationException: Operation not allowed` (Bedrock)**
Known issue — AWS account-level restriction being resolved. Use mock mode for all demos in the meantime.

**`docker compose exec` hangs or errors**
Make sure services are up: `docker compose ps`. If forge is not running, check `docker compose logs forge`.

---

## Kevin's Open Items

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

All active work is on `phase2-nova-demo`. PRs target `main` after Brandon reviews.

---

## Questions

Ping Brandon on Discord or drop a comment in the repo. Hackathon deadline: **March 16, 2026 @ 5pm PDT**.
