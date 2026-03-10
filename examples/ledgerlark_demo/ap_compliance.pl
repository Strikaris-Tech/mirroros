% ============================================================
% MirrorOS — LedgerLark AP Routing Compliance Rules
% File: examples/ledgerlark_demo/ap_compliance.pl
% ============================================================
% LedgerLark is the overseer agent that routes incoming bills
% to the correct accounting agent (clerk or auditor) before
% any approval action is taken.
%
% Gate 1 (routing):  violates_ap_policy(ledgerlark, route_bill(...), Reason)
% Gate 2 (approval): violates_ap_policy(Agent,      approve_bill(...), Reason)
% ============================================================

:- dynamic routed_to/2.   % routed_to(BillId, Agent) — asserted after routing

% ── Approved vendor registry ─────────────────────────────────────────────────

approved_vendor(office_supplies_co).
approved_vendor(cloud_infra_ltd).
approved_vendor(strikaris_dev).
approved_vendor(azure_services).
approved_vendor(acme_corp).

% ── Approval thresholds ───────────────────────────────────────────────────────

clerk_limit(1000).
auditor_limit(50000).

% ── Routing inference ─────────────────────────────────────────────────────────
% Determines which agent should handle a bill — used by the demo
% to display routing intent before asserting routed_to/2.

bill_agent(_BillId, Amount, VendorId, clerk) :-
    approved_vendor(VendorId),
    clerk_limit(Limit),
    Amount =< Limit.

bill_agent(_BillId, Amount, VendorId, auditor) :-
    approved_vendor(VendorId),
    clerk_limit(ClerkLimit),
    Amount > ClerkLimit,
    auditor_limit(AuditorLimit),
    Amount =< AuditorLimit.

% ── Routing policy violations ─────────────────────────────────────────────────

% Unapproved vendor — absolute block, no agent can override
violates_ap_policy(ledgerlark, route_bill(_BillId, _Amount, VendorId), unapproved_vendor) :-
    \+ approved_vendor(VendorId).

% Amount beyond all approval authority
violates_ap_policy(ledgerlark, route_bill(_BillId, Amount, _VendorId), exceeds_auditor_limit) :-
    auditor_limit(Limit),
    Amount > Limit.

% ── Approval policy violations ────────────────────────────────────────────────

% Clerk may not approve bills above their limit
violates_ap_policy(clerk, approve_bill(_BillId, Amount), exceeds_clerk_limit) :-
    clerk_limit(Limit),
    Amount > Limit.

% Agent may not approve a bill that was not routed to them
violates_ap_policy(Agent, approve_bill(BillId, _Amount), not_routed_to_agent) :-
    \+ routed_to(BillId, Agent).

% ============================================================
% Example queries:
%   ?- bill_agent('BILL-001', 450, office_supplies_co, Agent).
%   ?- violates_ap_policy(ledgerlark, route_bill('BILL-003', 300, unknown_co), R).
%   ?- violates_ap_policy(clerk, approve_bill('BILL-002', 8500), R).
% ============================================================
