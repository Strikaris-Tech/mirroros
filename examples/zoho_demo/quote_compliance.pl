% ============================================================
% File: examples/zoho_demo/quote_compliance.pl
% Purpose: Quote-to-cash governance rules for the Zoho demo
% ============================================================
% Governs Strikaris's quote-to-cash workflow:
%
%   Stage 1: create_quote       — is the agent authorised for this amount?
%   Stage 2: po_receipt         — external event, no gate required
%   Stage 3: approve_document   — does PO match quote within 2% tolerance?
%   Stage 4: start_fulfillment  — is the document verified?
%   Stage 5: generate_invoice   — is the document verified?
%
% Stage transition enforcement prevents any step from being skipped.
%
% Primary predicate: violates_quote_policy/3
%   violates_quote_policy(+Agent, +Action, -Reason)
%   Succeeds (with Reason bound) when the action is NOT permitted.
% ============================================================

% ── APPROVAL LIMITS ──────────────────────────────────────────────────────────
% quote_approval_limit(+Role, -MaxUSD)
% Maximum quote value a role may create without escalation.

quote_approval_limit(sales_rep, 20000).
quote_approval_limit(manager,  100000).

% ── STAGE TRANSITIONS ────────────────────────────────────────────────────────
% valid_transition(+From, +To)
% Enforces linear progression — no stage may be skipped.

valid_transition(quote_sent,          po_received).
valid_transition(po_received,         quote_approved).
valid_transition(quote_approved,      fulfillment_started).
valid_transition(fulfillment_started, invoice_sent).

% ── DYNAMIC STATE ─────────────────────────────────────────────────────────────
% Asserted at runtime by the Python orchestrator via MRSBridge.assert_fact().

:- dynamic document_verified/1.

% ── POLICY VIOLATION PREDICATES ───────────────────────────────────────────────

% Quote exceeds agent's approval authority.
violates_quote_policy(Agent, create_quote(_, Amount), Reason) :-
    quote_approval_limit(Agent, Limit),
    Amount > Limit,
    format(atom(Reason),
           'Exceeds quote authority: ~w limit is $~w', [Agent, Limit]).

% Stage transition not in valid sequence.
violates_quote_policy(_, advance_stage(From, To), Reason) :-
    \+ valid_transition(From, To),
    format(atom(Reason),
           'Invalid stage transition: ~w -> ~w', [From, To]).

% PO total deviates from quote total by more than 2%.
% This is the key document-verification gate — no role can override it.
violates_quote_policy(_, approve_document(_, POTotal, QuoteTotal), Reason) :-
    POTotal > 0, QuoteTotal > 0,
    Variance is abs(POTotal - QuoteTotal) / QuoteTotal * 100,
    Variance > 2.0,
    format(atom(Reason),
           'Document variance ~1f% exceeds 2%% tolerance (PO: $~w  Quote: $~w)',
           [Variance, POTotal, QuoteTotal]).

% Fulfillment requires a verified document for this quote.
violates_quote_policy(_, start_fulfillment(QuoteId), Reason) :-
    \+ document_verified(QuoteId),
    format(atom(Reason),
           'Fulfillment blocked: document not verified for ~w', [QuoteId]).

% Invoice generation requires a verified document for this quote.
violates_quote_policy(_, generate_invoice(QuoteId, _), Reason) :-
    \+ document_verified(QuoteId),
    format(atom(Reason),
           'Invoice blocked: document not verified for ~w', [QuoteId]).

% ── CODEX INTEGRATION (multifile extension) ──────────────────────────────────

:- multifile violates_codex/2.
:- discontiguous violates_codex/2.

violates_codex(Agent, create_quote(QuoteId, Amount)) :-
    violates_quote_policy(Agent, create_quote(QuoteId, Amount), _).

violates_codex(_, advance_stage(From, To)) :-
    violates_quote_policy(_, advance_stage(From, To), _).

violates_codex(_, approve_document(QuoteId, POTotal, QuoteTotal)) :-
    violates_quote_policy(_, approve_document(QuoteId, POTotal, QuoteTotal), _).

violates_codex(_, start_fulfillment(QuoteId)) :-
    violates_quote_policy(_, start_fulfillment(QuoteId), _).

violates_codex(_, generate_invoice(QuoteId, Amount)) :-
    violates_quote_policy(_, generate_invoice(QuoteId, Amount), _).

% ── TEST QUERIES ──────────────────────────────────────────────────────────────
%
%   ?- violates_quote_policy(sales_rep, create_quote('STR-2026-Q-018', 15000), R).
%   false.                             % $15,000 <= $20,000 limit
%
%   ?- violates_quote_policy(sales_rep, create_quote('STR-2026-Q-018', 25000), R).
%   R = 'Exceeds quote authority: sales_rep limit is $20000'.
%
%   ?- violates_quote_policy(_, approve_document('STR-2026-Q-018', 15000, 15000), R).
%   false.                             % 0% variance — exact match
%
%   ?- violates_quote_policy(_, approve_document('STR-2026-Q-018', 14500, 15000), R).
%   R = 'Document variance 3.3% exceeds 2% tolerance (PO: $14500  Quote: $15000)'.
%
%   ?- violates_quote_policy(_, start_fulfillment('STR-2026-Q-018'), R).
%   R = 'Fulfillment blocked: document not verified for STR-2026-Q-018'.
%   % (resolves to false after assertz(document_verified('STR-2026-Q-018')))
%
% ============================================================

% End of quote_compliance.pl
