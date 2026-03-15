#!/usr/bin/env bash
# demo.sh — MirrorOS full demo sequence for video recording
# Runs all 4 shots in order with a pause between each.
# Usage: bash demo.sh
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
AMBER="\033[33m"
DIM="\033[2m"
RESET="\033[0m"

_header() { echo -e "\n${BOLD}$1${RESET}\n"; }
_pause()  {
  echo -e "\n${AMBER}Press Enter when ready for the next shot...${RESET}"
  read -r
}

# ── Preflight ─────────────────────────────────────────────────────────────────

if ! command -v docker &>/dev/null; then
  echo "ERROR: docker not found." && exit 1
fi

if ! docker compose ps --services --filter status=running 2>/dev/null | grep -q forge; then
  _header "Starting services..."
  docker compose up -d
  echo -e "${GREEN}Services up.${RESET}"
fi

# ── Shot 1 — AP terminal only ─────────────────────────────────────────────────

_header "SHOT 1 — AP Orchestration (terminal only)"
echo -e "${DIM}All 4 bills, both gates, all 4 ledger seals.${RESET}\n"

docker compose exec -w /app forge python examples/ledgerlark_demo/ap_demo.py --no-browser

ACTION_DATE=$(date +%Y%m%d)
VERIFY_ID="ap_${ACTION_DATE}_003_route"

_pause

# ── Shot 2 — AP with Nova Act ─────────────────────────────────────────────────

_header "SHOT 2 — AP Orchestration (Nova Act + Zoho Books)"

if [[ -z "${NOVA_ACT_API_KEY:-}" ]]; then
  echo -e "${AMBER}NOVA_ACT_API_KEY not set — skipping browser shot.${RESET}"
  echo -e "${DIM}Set it and re-run, or run Shot 2 manually:${RESET}"
  echo -e "  ${DIM}python examples/ledgerlark_demo/ap_demo.py${RESET}\n"
else
  echo -e "${DIM}Make sure Chromium is open and logged into Zoho Books.${RESET}\n"
  python examples/ledgerlark_demo/ap_demo.py
fi

_pause

# ── Shot 3 — Ledger verify ────────────────────────────────────────────────────

_header "SHOT 3 — Ledger verification"
echo -e "${DIM}Verifying rejected bill seal: ${VERIFY_ID}${RESET}\n"

python -m ledger.verify "${VERIFY_ID}"

_pause

# ── Shot 4 — Cold start ───────────────────────────────────────────────────────

_header "SHOT 4 — Cold start"
echo -e "${DIM}Tearing down and running quickstart from scratch.${RESET}\n"

docker compose down -v
bash quickstart.sh

echo -e "\n${BOLD}${GREEN}All 4 shots complete.${RESET}"
