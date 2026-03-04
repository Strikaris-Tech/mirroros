%% concordance.pl — Rune-to-Clause Vocabulary Map
%%
%% Maps every Z3 surface predicate to its Prolog equivalent name and
%% argument-sort signature.
%%
%% Loaded at boot by MRSBridge._load_concordance().
%% Boot raises ConcordanceError if any Z3 predicate declared in
%% verifier/essence_runes.py lacks an entry here — drift is structurally
%% impossible after this check.
%%
%% Format:
%%   concordance(z3, 'Z3FunctionName', prolog, prolog_atom, [arg_sort, ...]).
%%
%% Argument sorts mirror the Z3 sort sequence:
%%   agent | resource | action | domain | evidence | commitment
%%
%% @canon — do not edit without a corresponding change to
%%          verifier/essence_runes.py and a passing boot check.

:- module(concordance, [concordance/5, z3_predicates/1]).

% ─── L1 Essence Runes: agent predicates ──────────────────────────────────────
% Properties carried by actors.
% Source: EssenceRunes.__init__ in verifier/essence_runes.py

% ☉  Charge — signature that distinguishes; identity
concordance(z3, 'Charge',    prolog, charge,    [agent]).

% ◎  OathRune — invariant promise binding word to deed
concordance(z3, 'OathRune',  prolog, oath_rune, [agent]).

% ∇  Potential — stored capacity; readiness to transform
concordance(z3, 'Potential', prolog, potential, [agent, resource]).

% ▲  Motion — directed impulse; the act of moving
concordance(z3, 'Motion',    prolog, motion,    [agent, resource]).

% Will — volitional bridge; agent selects action from potential
concordance(z3, 'Will',      prolog, will,      [agent, action]).

% ─── L1 Essence Runes: resource predicates ───────────────────────────────────
% Properties carried by things acted upon.
% Source: EssenceRunes.__init__ in verifier/essence_runes.py

% ◻︎  Matter — body that endures; mass-energy substrate
concordance(z3, 'Matter',      prolog, matter,      [resource]).

% ◯  Information — pattern that can copy; entropy carrier
concordance(z3, 'Information', prolog, information, [resource]).

% ✧  Spacetime — stage and boundary; coordinates + metric
concordance(z3, 'Spacetime',   prolog, spacetime,   [resource]).

% ⟐  Boundary — membrane that regulates flow; interface topology
concordance(z3, 'Boundary',    prolog, boundary,    [resource]).

% ─── L2 Relational Verbs ─────────────────────────────────────────────────────
% Structural relations between agents, resources, and domains.
% Source: EssenceRunes.__init__ (lines 75-88) in verifier/essence_runes.py

% Ownership — agent holds a resource
concordance(z3, 'Ownership',      prolog, owns,       [agent, resource]).

% Consent — grantor permits grantee access to resource
concordance(z3, 'Consent',        prolog, consent,    [agent, agent, resource]).

% Sovereignty — agent holds authority over a domain
concordance(z3, 'Sovereignty',    prolog, sovereign,  [agent, domain]).

% Stewardship — agent acts as steward on behalf of beneficiary over resource
concordance(z3, 'Stewardship',    prolog, stewards,   [agent, agent, resource]).

% can_access — agent may access resource (Z3 name is lowercase; matches code)
concordance(z3, 'can_access',     prolog, can_access, [agent, resource]).

% Witness — agent witnesses an action; audit anchor
% Note: Z3 signature is Witness(Agent, Action) — action, not resource
concordance(z3, 'Witness',        prolog, witness,    [agent, action]).

% Performs — agent performs an action
% Note: Z3 signature is Performs(Agent, Action) — no resource argument
concordance(z3, 'Performs',       prolog, performs,   [agent, action]).

% Transformation — agent transforms one resource into another
concordance(z3, 'Transformation', prolog, transforms, [agent, resource, resource]).

% Auditability — action is evidenced by artifact
concordance(z3, 'Auditability',   prolog, auditable,  [action, evidence]).

% ─── L2 Oath: binding commitment ─────────────────────────────────────────────
% Oath(Agent, Commitment) is the verb form — agent is bound to a commitment.
% Distinct from OathRune(Agent), which tests for the rune property alone.
% Source: CodexPrimitives.__init__ in verifier/codex_primitives.py

concordance(z3, 'Oath', prolog, oath, [agent, commitment]).

% ─── Introspection helper ─────────────────────────────────────────────────────
% Returns all Z3 predicate names registered in this concordance.
% Called by MRSBridge._verify_concordance_coverage() at boot.

% Test query:
% ?- z3_predicates(Names), length(Names, N), write(N), write(' predicates registered'), nl.
z3_predicates(Names) :-
    findall(Z3Name, concordance(z3, Z3Name, prolog, _, _), Names).
