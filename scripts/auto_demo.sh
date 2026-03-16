#!/usr/bin/env bash
# demo.sh — MirrorOS full demo sequence, timed for video recording
#
# Runs all 5 demo steps automatically with countdown pauses between steps
# so narration audio can be laid in during post-production. Tune the
# PAUSE_* values below to match your narration timing.
#
# Steps:
#   1  AP Orchestration (terminal)     — LedgerLark routes 4 bills through
#                                        the dual-gate MRS engine. Shows
#                                        PERMITTED / REJECTED verdicts with
#                                        latency and immudb seal per bill.
#                                        Opens arch diagram in browser after.
#   2  AP + Nova Act + Zoho Books      — Same routing, but approved bills
#                                        are recorded in Zoho Books by Nova
#                                        Act. Rejected bills never touch the
#                                        browser. Requires NOVA_ACT_API_KEY.
#   3  LedgerLark Invoice UI           — MRS-gated invoice approval with a
#                                        live verdict panel at localhost:7242.
#                                        Nova Act clicks through approvals if
#                                        key is set; otherwise approve manually.
#   4  Ledger verification             — Runs python -m ledger.verify against
#                                        the sealed routing decision for the
#                                        rejected bill (BILL-003). Prints the
#                                        Merkle proof and verified: true.
#   5  Cold start                      — Tears down all services and runs
#                                        quickstart.sh from scratch to prove
#                                        the system boots clean in < 60s.
#
# Prerequisites:
#   docker                  (required — all services run in containers)
#   NOVA_ACT_API_KEY        (optional — Steps 2 and 3 skip if not set)
#   /Applications/Chromium.app  (optional — falls back to system browser)
#
# Usage:
#   bash scripts/demo.sh
#   PAUSE_AFTER_STEP1=80 bash scripts/demo.sh   # override a pause
set -euo pipefail

PAUSE_AFTER_STEP1=65
PAUSE_AFTER_STEP2=15
PAUSE_AFTER_STEP3=12
PAUSE_AFTER_STEP4=8

BOLD="\033[1m"
GREEN="\033[32m"
AMBER="\033[33m"
CYAN="\033[36m"
DIM="\033[2m"
RESET="\033[0m"

# ── Helpers ──────────────────────────────────────────────────────────────────

_hr()      { echo -e "${DIM}$(printf '━%.0s' {1..60})${RESET}"; }

_step() {
  local n=$1 total=5 title="$2"
  echo ""
  _hr
  echo -e "  ${BOLD}${n}/${total}  ${title}${RESET}"
  _hr
  echo ""
}

_type() {
  local text="$1" delay=${2:-0.025}
  local i=0
  while [[ $i -lt ${#text} ]]; do
    printf '%s' "${text:$i:1}"
    sleep "$delay"
    i=$((i + 1))
  done
  echo ""
}

_run() {
  echo -e "${DIM}\$${RESET} ${CYAN}$*${RESET}"
  sleep 0.4
  "$@"
}

_pause() {
  local secs=$1 msg=${2:-""}
  local width=40 elapsed=0
  if [[ -n "$msg" ]]; then
    echo -e "\n${DIM}${msg}${RESET}"
  fi
  while [[ $elapsed -lt $secs ]]; do
    local filled=$((elapsed * width / secs))
    local empty=$((width - filled))
    local remaining=$((secs - elapsed))
    printf "\r  ${DIM}$(printf '█%.0s' $(seq 1 $filled 2>/dev/null))$(printf '░%.0s' $(seq 1 $empty 2>/dev/null))  %ds${RESET}" "$remaining"
    sleep 1
    elapsed=$((elapsed + 1))
  done
  printf "\r%-60s\r" " "
}

# ── Preflight ────────────────────────────────────────────────────────────────

if ! command -v docker &>/dev/null; then
  echo "ERROR: docker not found." && exit 1
fi

if ! docker compose ps --services --filter status=running 2>/dev/null | grep -q forge; then
  echo -e "\n${DIM}Starting services...${RESET}"
  docker compose up -d
  echo -e "${GREEN}Services up.${RESET}"
  sleep 2
fi

echo -e "\n${BOLD}MirrorOS${RESET}  ${DIM}Demo Recording${RESET}\n"
_hr
echo -e "  ${DIM}Forge        ${RESET}${GREEN}running${RESET}"
echo -e "  ${DIM}MRS Bridge   ${RESET}${GREEN}ready${RESET}"
echo -e "  ${DIM}Nova Act     ${RESET}$(if [[ -n \"${NOVA_ACT_API_KEY:-}\" ]]; then echo -e \"${GREEN}ready${RESET}\"; else echo -e \"${DIM}not configured${RESET}\"; fi)"
echo -e "  ${DIM}Ledger       ${RESET}${GREEN}active${RESET}"
_hr
sleep 3

# ── Step 1 — AP Orchestration (terminal) ─────────────────────────────────────

_step 1 "AP Orchestration"
_type "Processing 4 bills through dual-gate policy engine..."
sleep 1

_run docker compose exec -w /app forge python examples/ledgerlark_demo/ap_demo.py --no-browser

ACTION_DATE=$(date +%Y%m%d)
VERIFY_ID="ap_${ACTION_DATE}_003_route"

_pause 58
ARCH_HTML="$(pwd)/examples/ledgerlark_demo/arch_diagram.html"
# Open arch diagram — try Chromium first, fall back to system default browser
open -a /Applications/Chromium.app "$ARCH_HTML" 2>/dev/null \
  || open "$ARCH_HTML" 2>/dev/null \
  || xdg-open "$ARCH_HTML" 2>/dev/null \
  || true
_pause $((PAUSE_AFTER_STEP1 - 58))

# ── Step 2 — AP with Nova Act + Zoho ─────────────────────────────────────────

_step 2 "Browser Automation (Nova Act + Zoho Books)"

if [[ -z "${NOVA_ACT_API_KEY:-}" ]]; then
  echo -e "${AMBER}NOVA_ACT_API_KEY not set — skipping browser step.${RESET}"
  echo -e "${DIM}Set it and re-run, or run manually:${RESET}"
  echo -e "  ${DIM}python examples/ledgerlark_demo/ap_demo.py${RESET}\n"
else
  _type "Connecting to Zoho Books via CDP..."
  sleep 1
  _run python examples/ledgerlark_demo/ap_demo.py --max-bills 2
fi

_pause $PAUSE_AFTER_STEP2

# ── Step 3 — LedgerLark Invoice UI ───────────────────────────────────────────

_step 3 "Invoice Approval UI"

if [[ -z "${NOVA_ACT_API_KEY:-}" ]]; then
  echo -e "${AMBER}NOVA_ACT_API_KEY not set — open http://localhost:7242 and approve manually.${RESET}\n"
  docker compose exec -w /app forge python examples/accounting_demo/server.py &
  SERVER_PID=$!
  echo -e "${DIM}Server started at http://localhost:7242${RESET}"
  echo -e "${DIM}Press Enter when done recording...${RESET}"
  read -r
  kill $SERVER_PID 2>/dev/null || true
else
  _type "Starting invoice server on :7242..."
  docker compose exec -w /app forge python examples/accounting_demo/server.py &
  SERVER_PID=$!
  sleep 2
  _run python examples/accounting_demo/nova_demo.py
  kill $SERVER_PID 2>/dev/null || true
fi

_pause $PAUSE_AFTER_STEP3

# ── Step 4 — Ledger verify ───────────────────────────────────────────────────

_step 4 "Ledger Verification"
_type "Verifying tamper-proof seal for rejected bill..."
sleep 1

echo -e "${DIM}\$${RESET} ${CYAN}python -m ledger.verify ${VERIFY_ID}${RESET}"
sleep 0.4
python -m ledger.verify "${VERIFY_ID}"

_pause $PAUSE_AFTER_STEP4

# ── Step 5 — Cold start ─────────────────────────────────────────────────────

_step 5 "Cold Start"
_type "Tearing down all services and running from scratch..."
sleep 1

_run docker compose down -v
_run bash quickstart.sh

echo ""
_hr
echo -e "  ${BOLD}${GREEN}Demo complete.${RESET}"
_hr
echo ""
