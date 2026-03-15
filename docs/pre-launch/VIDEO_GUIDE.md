# MirrorOS — Demo Video Guide

Submission requires a ~3 minute video. This doc covers the recording setup, narration tools, and the exact script with commands.

---

## Tools

### Screen Recording
- **QuickTime Player** (macOS) — File → New Screen Recording. Simple, no install needed.
- **OBS Studio** — free, more control over layout (terminal + browser side by side). Worth it if you want to show both at once.

### AI Narration
- **ElevenLabs** (elevenlabs.io) — paste the script, download the audio file, drop it over the recording. Best voice quality, free tier handles a 3-minute clip. Fastest path.
- **Descript** (descript.com) — record screen + voice together, edit by editing a transcript, overdub with AI voice. Better if you want to iterate on timing. Steeper setup but more control.

**Recommended for speed:** ElevenLabs for audio + QuickTime for screen → combine in iMovie or CapCut.

---

## Demo Flow — Exact Commands

Run these in order. Have Docker running before you start recording.

### Before you hit record
```bash
docker compose up -d
```

### Shot 1 — AP terminal (no browser) [~0:18]
```bash
docker compose exec -w /app forge python examples/ledgerlark_demo/ap_demo.py --no-browser
```
Let the full output scroll. All 4 bills, both gates, ledger seals.

### Shot 2 — AP demo with Nova Act live in Zoho [~1:20]
Make sure Chromium is already open and logged into Zoho Books first.
```bash
python examples/ledgerlark_demo/ap_demo.py
```
Nova Act will connect to your existing Chromium session via CDP on port 9222.

### Shot 3 — Ledger verification [~2:20]
Grab the action ID from the BILL-003 rejection in Shot 1 output (format: `ap_YYYYMMDD_003_route`):
```bash
python -m ledger.verify ap_YYYYMMDD_003_route
```
Should return `"verified": true` with a tx ID.

### Shot 4 — Quickstart cold start close [~2:38]
```bash
docker compose down -v && bash quickstart.sh
```

---

## Narration Script

**[0:00 — docker compose up -d running, or cut straight to terminal]**

AI agents are taking real actions right now. Approving invoices. Routing payments. Modifying records. The governance story for almost all of them is the same: we wrote a careful prompt, and it usually does the right thing.

That is not governance. That is hope.

---

**[0:18 — ap_demo.py --no-browser output scrolling]**

This is MirrorOS. LedgerLark is an accounts payable agent. Before it touches anything, every bill passes two gates — Prolog behavioral verification and Z3 formal proof.

Four bills. Watch what happens.

Office Supplies Co, four hundred fifty dollars. Approved vendor, within clerk authority. Permitted — routed to clerk. Ledger sealed.

Cloud Infra, eighty-five hundred. Approved vendor, exceeds clerk limit. Routed to auditor. Permitted. Sealed.

Unknown Vendor Co, three hundred dollars. Not in the approved registry. Rejected at the routing gate — before any agent touches it, before any system is called. Sealed.

Strikaris Dev, fifteen thousand. Auditor authority. Permitted. Sealed.

Every verdict is cryptographically sealed in immudb — a Merkle-tree ledger. That rejection wasn't just logged. It was proven.

---

**[1:20 — ap_demo.py with Nova Act, Zoho Books visible in browser]**

Now watch it with Nova Act executing.

Here's the key architectural distinction. In a standard Nova Act integration, the language model decides whether an action is allowed. The governance lives in a prompt. It's probabilistic. It can be rephrased or hallucinated around.

In MirrorOS, Nova Act is a cursor. By the time it receives an instruction, Prolog has already ruled, Z3 has already verified, and the verdict is sealed in the ledger. Nova Act is never asked whether the action is allowed. It is only told what to click.

Watch bill three — Unknown Vendor Co. Rejected at the gate. Nova Act never moves. The browser is untouched. You cannot prompt-inject your way past a Prolog predicate.

---

**[2:20 — ledger.verify command, verified: true output]**

Pull the rejected bill's action ID. Verified true. The Merkle proof matches the tree root. That record has not been altered since the moment it was written.

This is not application logging. This is structural immutability.

---

**[2:38 — quickstart cold start]**

MirrorOS Core is open source. Docker is all you need. Clone it, run it, see governed pulses in under sixty seconds.

Any agent. Any system. Any MCP tool call. If it declares intent, MirrorOS governs it — proven before it executes, sealed after.

---

## Tips

- Get to the terminal output within the first 30 seconds — don't linger on slides or talking heads.
- Record at 1600×900 if possible — matches the Chromium profile window size.
- Do a dry run of the full sequence before recording. The Nova Act session can take a moment to connect on first launch.
- Grab the real `ap_YYYYMMDD_003_route` action ID from your dry run output so it's ready for Shot 3.
- Add `#AmazonNova` to the video description on Devpost.
