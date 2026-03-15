#!/usr/bin/env bash
# demo.sh — MirrorOS full demo sequence for video recording
#
# Shots are timed to match the narration script (~3 min total):
#   Shot 1  0:18 – 1:20   AP terminal only       (~62s buffer after)
#   Shot 2  1:20 – 2:20   AP + Nova Act          (~60s buffer after)
#   Shot 3  2:20 – 2:38   Ledger verify          (~18s buffer after)
#   Shot 4  2:38 – 3:00   Cold start / quickstart
#
# Tune the PAUSE_* values (seconds) if your narration runs faster/slower.
#
# Usage: bash demo.sh
set -euo pipefail

PAUSE_AFTER_SHOT1=8   # breathing room before Shot 2 narration kicks in
PAUSE_AFTER_SHOT2=6   # breathing room before Shot 3 narration kicks in
PAUSE_AFTER_SHOT3=4   # breathing room before Shot 4 narration kicks in

BOLD="\033[1m"
GREEN="\033[32m"
AMBER="\033[33m"
DIM="\033[2m"
RESET="\033[0m"

_header()     { echo -e "\n${BOLD}$1${RESET}\n"; }
_countdown()  {
  local secs=$1 label=${2:-"Next shot in"}
  for i in $(seq "$secs" -1 1); do
    printf "\r${AMBER}%s %ds...${RESET} " "$label" "$i"
    sleep 1
  done
  printf "\r%-40s\r" " "  # clear the line
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

_countdown $PAUSE_AFTER_SHOT1 "Shot 2 in"

# ── Shot 2 — AP with Nova Act ─────────────────────────────────────────────────

_header "SHOT 2 — AP Orchestration (Nova Act + Zoho Books)"

if [[ -z "${NOVA_ACT_API_KEY:-}" ]]; then
  echo -e "${AMBER}NOVA_ACT_API_KEY not set — skipping browser shot.${RESET}"
  echo -e "${DIM}Set it and re-run, or run Shot 2 manually:${RESET}"
  echo -e "  ${DIM}python examples/ledgerlark_demo/ap_demo.py${RESET}\n"
else
  echo -e "${DIM}Chromium should already be open and logged into Zoho Books.${RESET}\n"
  python examples/ledgerlark_demo/ap_demo.py
fi

_countdown $PAUSE_AFTER_SHOT2 "Shot 3 in"

# ── Shot 3 — Ledger verify ────────────────────────────────────────────────────

_header "SHOT 3 — Ledger verification"
echo -e "${DIM}Verifying rejected bill seal: ${VERIFY_ID}${RESET}\n"

python -m ledger.verify "${VERIFY_ID}"

_countdown $PAUSE_AFTER_SHOT3 "Shot 4 in"

# ── Shot 4 — Cold start ───────────────────────────────────────────────────────

_header "SHOT 4 — Cold start"
echo -e "${DIM}Tearing down and running quickstart from scratch.${RESET}\n"

docker compose down -v
bash quickstart.sh

echo -e "\n${BOLD}${GREEN}All 4 shots complete.${RESET}"
