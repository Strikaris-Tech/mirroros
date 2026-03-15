#!/usr/bin/env bash
# demo.sh — MirrorOS full demo sequence for video recording
#
# Shot 1   AP terminal only          (no browser, no API key)
# Shot 2   AP + Nova Act + Zoho      (browser automation)
# Shot 3   LedgerLark Invoice UI     (localhost:7242 + nova_demo.py)
# Shot 4   Ledger verify             (verify rejected bill seal)
# Shot 5   Cold start / quickstart
#
# Tune the PAUSE_* values (seconds) if your narration runs faster/slower.
#
# Usage: bash demo.sh
set -euo pipefail

PAUSE_AFTER_SHOT1=8
PAUSE_AFTER_SHOT2=6
PAUSE_AFTER_SHOT3=4
PAUSE_AFTER_SHOT4=4

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

# ── Shot 3 — LedgerLark Invoice UI ───────────────────────────────────────────

_header "SHOT 3 — LedgerLark Invoice UI (localhost:7242)"

if [[ -z "${NOVA_ACT_API_KEY:-}" ]]; then
  echo -e "${AMBER}NOVA_ACT_API_KEY not set — open http://localhost:7242 and approve manually.${RESET}\n"
  docker compose exec -w /app forge python examples/accounting_demo/server.py &
  SERVER_PID=$!
  echo -e "${DIM}Server started. Open http://localhost:7242 in your browser.${RESET}"
  echo -e "${DIM}Press Enter when done recording the UI...${RESET}"
  read -r
  kill $SERVER_PID 2>/dev/null || true
else
  echo -e "${DIM}Starting UI server and running nova_demo.py against it.${RESET}"
  echo -e "${DIM}Open http://localhost:7242 now — Nova Act will drive it.${RESET}\n"
  docker compose exec -w /app forge python examples/accounting_demo/server.py &
  SERVER_PID=$!
  sleep 2  # let server come up
  python examples/accounting_demo/nova_demo.py
  kill $SERVER_PID 2>/dev/null || true
fi

_countdown $PAUSE_AFTER_SHOT3 "Shot 4 in"

# ── Shot 4 — Ledger verify ────────────────────────────────────────────────────

_header "SHOT 4 — Ledger verification"
echo -e "${DIM}Verifying rejected bill seal: ${VERIFY_ID}${RESET}\n"

python -m ledger.verify "${VERIFY_ID}"

_countdown $PAUSE_AFTER_SHOT4 "Shot 5 in"

# ── Shot 5 — Cold start ───────────────────────────────────────────────────────

_header "SHOT 5 — Cold start"
echo -e "${DIM}Tearing down and running quickstart from scratch.${RESET}\n"

docker compose down -v
bash quickstart.sh

echo -e "\n${BOLD}${GREEN}All 5 shots complete.${RESET}"
