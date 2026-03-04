% ============================================================
% File: examples/accounting_demo/accounting_compliance.pl
% Purpose: Accounting governance rules for the MirrorOS demo
% ============================================================
% Load this module into MRSBridge after the core Codex:
%   bridge.load_module("examples/accounting_demo/accounting_compliance.pl")
%
% This file demonstrates how to extend the MRS Codex with domain-
% specific compliance rules.  Two mechanisms are used:
%
%   1. violates_accounting_policy/3 — agent-aware, reason-returning
%      predicate queried directly by the AccountingAdapter.
%
%   2. Multifile extension of violates_codex/2 — integrates with the
%      standard can_act/2 path so Codex_Laws.pl enforces accounting
%      limits automatically.
%
% Replace approval_limit/2 and vendor_verified/1 facts with your own
% domain data.  The predicate contracts remain stable.
% ============================================================

% ── APPROVAL LIMITS ─────────────────────────────────────────────────────────
% approval_limit(+Agent, -Limit)
% Maximum invoice amount (USD) an agent may approve unilaterally.

approval_limit(clerk,    1000).
approval_limit(auditor, 50000).

% ── VERIFIED VENDOR REGISTRY ────────────────────────────────────────────────
% vendor_verified(+VendorId)
% Only listed vendors may receive payments.

vendor_verified(acme_corp).
vendor_verified(trusted_supplier).
vendor_verified(city_utilities).

% ── POLICY VIOLATION PREDICATES (with reasons) ──────────────────────────────
% violates_accounting_policy(+Agent, +Action, -Reason)
% Called by AccountingAdapter._gate() before every write action.
% Succeeds (with Reason bound) when the action is NOT permitted.

violates_accounting_policy(Agent, approve_payment(_, Amount), Reason) :-
    approval_limit(Agent, Limit),
    Amount > Limit,
    format(atom(Reason),
           'Exceeds approval authority: ~w limit is ~w', [Agent, Limit]).

violates_accounting_policy(_, pay_vendor(Vendor, _), Reason) :-
    \+ vendor_verified(Vendor),
    format(atom(Reason),
           'Vendor not in approved list: ~w', [Vendor]).

% ── CODEX INTEGRATION (multifile extension) ──────────────────────────────────
% Extend violates_codex/2 so that can_act/2 (from Codex_Laws.pl) also
% enforces accounting policy automatically.  This means any call to
% bridge.check_authorization() is subject to these rules without any
% additional queries.

:- multifile violates_codex/2.
:- discontiguous violates_codex/2.

violates_codex(Agent, approve_payment(_, Amount)) :-
    approval_limit(Agent, Limit),
    Amount > Limit.

violates_codex(_, pay_vendor(Vendor, _)) :-
    \+ vendor_verified(Vendor).

% ── TEST QUERIES ─────────────────────────────────────────────────────────────
% Load this file then run:
%
%   ?- violates_accounting_policy(clerk, approve_payment(inv_001, 200), R).
%   false.                             % 200 <= 1000 — no violation
%
%   ?- violates_accounting_policy(clerk, approve_payment(inv_002, 25000), R).
%   R = 'Exceeds approval authority: clerk limit is 1000'.
%
%   ?- violates_accounting_policy(auditor, approve_payment(inv_002, 25000), R).
%   false.                             % 25000 <= 50000 — permitted
%
%   ?- violates_accounting_policy(clerk, pay_vendor(unknown_co, 500), R).
%   R = 'Vendor not in approved list: unknown_co'.
%
%   ?- violates_codex(clerk, approve_payment(inv_001, 200)).
%   false.
%
%   ?- violates_codex(clerk, approve_payment(inv_002, 25000)).
%   true.
% ============================================================

% End of accounting_compliance.pl
