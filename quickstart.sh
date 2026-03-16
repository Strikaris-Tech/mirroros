#!/usr/bin/env bash
# quickstart.sh — MirrorOS demo: Docker Compose up + 5 governed pulses in < 60s
# Requirements: Docker only. Everything runs inside the container.
set -euo pipefail

FORGE_PORT="${FORGE_PORT:-8767}"

BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
RESET="\033[0m"

echo -e "${BOLD}MirrorOS Quickstart${RESET}"
echo "---"

# ── Preflight ────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo -e "${RED}ERROR: 'docker' not found. Please install Docker and re-run.${RESET}"
  exit 1
fi

# ── Bring up services ────────────────────────────────────────────────────────
echo "Starting services..."
docker compose up -d --build --force-recreate 2>&1 | grep -E "Started|Running|built|error|Built" || true

# Wait for Forge to be reachable
echo "Waiting for Forge API (port ${FORGE_PORT})..."
for i in $(seq 1 20); do
  if curl -sf "http://localhost:${FORGE_PORT}/" > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -sf "http://localhost:${FORGE_PORT}/" > /dev/null 2>&1; then
  echo -e "${RED}Forge API did not come up in time. Check: docker compose logs forge${RESET}"
  exit 1
fi

echo -e "${GREEN}Forge is up.${RESET}"
echo ""

# ── Run 5 demo pulses inside the container ────────────────────────────────
echo -e "${BOLD}Running 5 governed demo pulses...${RESET}"
echo ""

docker compose exec -T forge python -c '
import time
from pathlib import Path
from mrs.bridge.mrs_bridge import MRSBridge

bridge = MRSBridge()

# Load AP compliance rules (clerk limits, vendor approval, auditor limits)
compliance = Path("/app/examples/ledgerlark_demo/ap_compliance.pl")
if compliance.exists():
    bridge.load_module(str(compliance))
else:
    print("WARNING: ap_compliance.pl not found — governance rules will not fire")

GREEN = "\033[32m"
RED   = "\033[31m"
AMBER = "\033[33m"
RESET = "\033[0m"

# Assert routing facts — in the full AP demo these are set by Gate 1 (routing)
# before Gate 2 (approval). The quickstart pre-asserts them to mirror that flow.
bridge.assert_fact("routed_to(inv_001, clerk)")
bridge.assert_fact("routed_to(inv_002, auditor)")

# 5 governed pulses — same scenario as the explainer doc
pulses = [
    ("clerk",   "approve_payment",  "approve_bill(inv_001, 200)",
     "violates_ap_policy(clerk, approve_bill(inv_001, 200), Reason)"),
    ("clerk",   "approve_payment",  "approve_bill(inv_002, 25000)",
     "violates_ap_policy(clerk, approve_bill(inv_002, 25000), Reason)"),
    ("clerk",   "pay_vendor",       "route_bill(inv_003, 500, unknown_co)",
     "violates_ap_policy(ledgerlark, route_bill(inv_003, 500, unknown_co), Reason)"),
    ("auditor", "approve_payment",  "approve_bill(inv_002, 25000)",
     "violates_ap_policy(auditor, approve_bill(inv_002, 25000), Reason)"),
    ("auditor", "compliance_check", "compliance_check(monthly_ledger)",
     "violates_ap_policy(auditor, compliance_check(monthly_ledger), Reason)"),
]

for agent, label, display_action, query in pulses:
    t0 = time.perf_counter()
    violations = bridge.query(query)
    latency_ms = (time.perf_counter() - t0) * 1000
    permitted = not violations
    reason = str(violations[0].get("Reason", "policy violation")) if violations else ""

    verdict = f"{GREEN}PERMITTED{RESET}" if permitted else f"{RED}REJECTED {RESET}"
    suffix = f"  {AMBER}{reason}{RESET}" if reason else ""
    print(f"  {verdict}  {agent:<10} {label:<20} ({latency_ms:.1f}ms){suffix}")

    bridge._log_reasoning(
        agent=agent,
        action=display_action,
        status="PERMITTED" if permitted else "REJECTED",
        details={"reason": reason, "latency_ms": round(latency_ms, 2)},
    )

print()
print("5 pulses complete. Check mrs/memory/reasoning_log.json for the sealed audit trail.")
'

echo ""
echo -e "${GREEN}${BOLD}Done.${RESET}"
echo "Forge API:    http://localhost:${FORGE_PORT}"
echo "API docs:     http://localhost:${FORGE_PORT}/docs"
echo "FlameConsole: http://localhost:5173  (if console service is running)"
