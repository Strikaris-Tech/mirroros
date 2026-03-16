% ========================================
% = Mirrors Reasoning Stack (MRS)
% File: prolog/Codex_Laws.pl
% Purpose: Core Codex laws governing all Mirrors
% ========================================
% Author: MirrorOS Contributors
% Version: 1.0
% ========================================

% Dynamic predicates allow runtime assertion and retraction
:- dynamic agent/2.
:- dynamic oath/2.
:- dynamic action/3.
:- dynamic memory_fact/2.
:- dynamic owns/2.
:- dynamic stewards/3.

% Consent: consent(Grantor, Grantee, Resource)
% Aligned with L2 concordance vocabulary [agent, agent, resource].
% Grantor must own the resource for consent to be valid (enforced by
% valid_consent/3 below).
:- dynamic consent/3.

% Allow domain files (*.dom) to add their own oath contradictions
:- discontiguous contradicts_oath/2.
:- dynamic contradicts_oath/2.

% ========================================
%  CODEX LAW 1  OATH INTEGRITY
% ========================================
% An agent must honor its Oaths in all actions.
% Violation occurs when action contradicts the Oath pattern.

violates_codex(Agent, Action) :-
    agent(Agent, Attributes),
    member(oath(Oath), Attributes),
    contradicts_oath(Oath, Action).

% Contradictions for each core Oath
% NOTE: contradicts_oath/2 does not receive the acting agent, so the
% authorization check below uses _ (existential). This means guard_memory
% is only violated when NO agent at all is authorized for Target.
% Per-agent authorization is enforced separately by can_act/2's call to
% unauthorized_memory_modification/2, which binds the specific agent.
% Future: consider contradicts_oath/3 to tighten this gate.
contradicts_oath(guard_memory, modify_memory(Target)) :-
    \+ authorized_memory_access(_, Target).

contradicts_oath(guard_memory, delete_memory(_)).
contradicts_oath(maintain_vault, delete_memory(_)).
contradicts_oath(protect_flame, extinguish_flame).
contradicts_oath(teach_pattern, spread_falsehood).

% ========================================
% > CODEX LAW 2  MEMORY SOVEREIGNTY
% ========================================
% No agent may modify or delete another agent's memory
% without explicit consent from the owner.

unauthorized_memory_modification(Agent, Target) :-
    Agent \= Target,
    action(Agent, modify_memory(Target), _),
    \+ has_resource_consent(Agent, Target).

unauthorized_memory_modification(Agent, Target) :-
    Agent \= Target,
    action(Agent, delete_memory(Target), _),
    \+ has_resource_consent(Agent, Target).

% Check if Agent has valid consent over Resource from its owner.
% consent(Owner, Agent, Resource) is valid only when Owner actually owns Resource.
% This closes Gap 1: consent facts are now semantically active only when
% the grantor genuinely owns the resource.
% Test query: ?- has_resource_consent(ledgerlark, audit_vault).
has_resource_consent(Agent, Resource) :-
    consent(Owner, Agent, Resource),
    owns(Owner, Resource).

% ========================================
% =
% CODEX LAW 3  TRANSPARENCY & AUDITABILITY
% ========================================
% All state-changing actions must be logged for review.
% Mirrors must not act in darkness.

requires_logging(Agent, Action) :-
    modifies_state(Action),
    agent(Agent, _).

modifies_state(modify_memory(_)).
modifies_state(assert_fact(_)).
modifies_state(retract_fact(_)).
modifies_state(delete_memory(_)).
modifies_state(grant_consent(_,_,_)).
modifies_state(revoke_consent(_,_,_)).

% ========================================
% > AUTHORIZATION AND PERMISSION SYSTEM
% ========================================

% Self-access is always permitted
authorized_memory_access(Agent, self) :-
    agent(Agent, _).

% Access through granted consent (aligned with L2 concordance model)
% consent(Owner, Agent, Resource) -> Owner grants Agent access to Resource
authorized_memory_access(Agent, Target) :-
    has_resource_consent(Agent, Target).

% Domain-based authorization
authorized_memory_access(Agent, Target) :-
    agent(Agent, Attrs),
    member(domain(Domain), Attrs),
    memory_in_domain(Target, Domain).

% Memorydomain mapping helper
memory_in_domain(Target, Domain) :-
    memory_fact(Target, metadata(domain(Domain))).

% ========================================
% = ACTION PERMISSION LAYER
% ========================================

can_act(Agent, Action) :-
    agent(Agent, _),
    \+ violates_codex(Agent, Action),
    \+ unauthorized_memory_modification(Agent, _).

% ========================================
% > CONSENT MANAGEMENT
% ========================================

% Grant consent: Granter gives Grantee access to Resource.
% Precondition: Granter must own the Resource.
% consent(Granter, Grantee, Resource) -> aligned with L2 concordance.
% Test query: ?- grant_consent(mirror_host, ledgerlark, audit_vault).
grant_consent(Granter, Grantee, Resource) :-
    agent(Granter, _),
    agent(Grantee, _),
    owns(Granter, Resource),
    assertz(consent(Granter, Grantee, Resource)),
    requires_logging(Granter, grant_consent(Granter, Grantee, Resource)).

% Revoke consent
revoke_consent(Granter, Grantee, Resource) :-
    retract(consent(Granter, Grantee, Resource)),
    requires_logging(Granter, revoke_consent(Granter, Grantee, Resource)).

% ========================================
% > INFERENCE HELPERS
% ========================================

% Would the new fact contradict existing laws?
would_contradict(Agent, NewFact) :-
    assertz(NewFact),
    violates_codex(Agent, _),
    retract(NewFact).

% List all resources an agent has been granted consent to access
agent_permissions(Agent, Resources) :-
    findall(Resource, (consent(_, Agent, Resource), has_resource_consent(Agent, Resource)), Resources).

% Identify all agents who granted consent to a given agent
granted_by(Agent, Granters) :-
    findall(G, consent(G, Agent, _), Granters).

% ========================================
%  COLLABORATION COMPATIBILITY
% ========================================

compatible_for_task(A1, A2, Task) :-
    A1 \= A2,
    can_collaborate_on(A1, Task),
    can_collaborate_on(A2, Task).

can_collaborate_on(Agent, Task) :-
    agent(Agent, Attrs),
    member(domain(Domain), Attrs),
    task_in_domain(Task, Domain).

task_in_domain(memory_maintenance, memory_core).
task_in_domain(code_review, code_review).
task_in_domain(vault_access, memory_core).
task_in_domain(reasoning, reasoning).
task_in_domain(verification, reasoning).
task_in_domain(bill_tracking, financial).
task_in_domain(cashflow_analysis, financial).
task_in_domain(compliance_check, financial).
task_in_domain(erp_design, erp).
task_in_domain(erp_integration, erp).
task_in_domain(ledger_reconciliation, erp).
task_in_domain(gl_validation, erp).

% ========================================
% > TEST QUERIES (Examples)
% ========================================
% ?- agent(ledgerlark, [oath(guard_memory), role(sentinel)]).
% ?- can_act(ledgerlark, modify_memory(self)).
% ?- violates_codex(ledgerlark, delete_memory(courier)).
% ?- grant_consent(mirror_host, ledgerlark, audit_vault).  % requires owns(mirror_host, audit_vault)
% ?- authorized_memory_access(ledgerlark, audit_vault).    % requires valid consent chain
% ?- has_resource_consent(ledgerlark, audit_vault).        % checks consent + ownership
% ========================================

% End of Codex_Laws.pl
