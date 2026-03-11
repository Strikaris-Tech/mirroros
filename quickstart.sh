
#!/usr/bin/env bash
# quickstart.sh — MirrorOS demo: Docker Compose up + 5 governed pulses in < 60s
PYTHON_CMD=$(command -v python3 || command -v python)
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
RESET="\033[0m"

echo -e "${BOLD}MirrorOS Quickstart${RESET}"
echo "---"

# ── Preflight ────────────────────────────────────────────────────────────────
for cmd in docker $PYTHON_CMD; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}ERROR: '$cmd' not found. Please install it and re-run.${RESET}"
    exit 1
  fi
done

# ── Bring up services ────────────────────────────────────────────────────────
echo "Starting services..."
docker compose up -d --build 2>&1 | grep -E "Started|Running|built|error" || true

# Wait for Forge to be reachable
echo "Waiting for Forge API (port 8765)..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8765/ > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -sf http://localhost:8765/ > /dev/null 2>&1; then
  echo -e "${RED}Forge API did not come up in time. Check: docker compose logs forge${RESET}"
  exit 1
fi

echo -e "${GREEN}Forge is up.${RESET}"
echo ""

# ── Run 5 demo pulses ────────────────────────────────────────────────────────
echo -e "${BOLD}Running 5 governed demo pulses...${RESET}"
echo ""

$PYTHON_CMD - <<'EOF'
import sys
import json

sys.path.insert(0, ".")

try:
    from mrs.bridge.mrs_bridge import MRSBridge
except ImportError:
    print("MRS bridge not importable — install dependencies: pip install -r forge/requirements.txt")
    sys.exit(1)

bridge = MRSBridge()

pulses = [
    ("clerk",   "approve_payment", {"amount": 200,    "invoice": "inv_001"}),
    ("clerk",   "approve_payment", {"amount": 25000,  "invoice": "inv_002"}),
    ("clerk",   "pay_vendor",      {"vendor": "unknown_co", "amount": 500}),
    ("auditor", "approve_payment", {"amount": 25000,  "invoice": "inv_002"}),
    ("auditor", "compliance_check",{"scope": "monthly_ledger"}),
]

GREEN = "\033[32m"
RED   = "\033[31m"
RESET = "\033[0m"

for agent, action, params in pulses:
    result = bridge.check_authorization(agent, action, params)
    permitted = result.get("permitted", False)
    verdict = f"{GREEN}PERMITTED{RESET}" if permitted else f"{RED}REJECTED {RESET}"
    reason = result.get("reason", "")
    latency = result.get("latency_ms", 0)
    print(f"  {verdict}  {agent:<10} {action:<20} ({latency:.1f}ms)  {reason}")

print()
print("5 pulses complete. Check mrs/memory/reasoning_log.json for the sealed audit trail.")
EOF

echo ""
echo -e "${GREEN}${BOLD}Done.${RESET}"
echo "Forge API:    http://localhost:8765"
echo "API docs:     http://localhost:8765/docs"
echo "FlameConsole: http://localhost:5173  (if console service is running)"
