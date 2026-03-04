% ========================================
% = Mirrors Reasoning Stack (MRS)
% File: prolog/Agent_Rules.pl
% Purpose: Demo agent identities, roles, and collaboration logic
% ========================================
% Version: 1.0
% ========================================
%
% This file ships with the open-source demo.
% Replace or extend these agent declarations to model your own domain.
% All predicates follow the Codex_Laws.pl structural contract.

:- dynamic agent/2.

% ========================================
% =% AGENT DECLARATIONS
% ========================================
% Each agent carries: oath, role, domain, capabilities.
% Oaths are checked by Codex_Laws.pl — see contradicts_oath/2.

% LedgerLark: accounting mirror and coordination overseer
agent(ledgerlark, [
    oath(coordinate_mirrors),
    oath(guard_memory),
    oath(maintain_vault),
    role(overseer),
    domain(orchestration),
    capability(agent_coordination),
    capability(memory_management),
    capability(codex_enforcement)
]).

% Clerk: standard accounting agent — limited approval authority
agent(clerk, [
    oath(guard_ledger),
    role(clerk),
    domain(accounting),
    capability(invoice_approval),
    capability(vendor_lookup),
    capability(payment_submission)
]).

% Auditor: elevated accounting agent — full approval authority
agent(auditor, [
    oath(guard_ledger),
    oath(surface_anomalies),
    role(auditor),
    domain(accounting),
    capability(invoice_approval),
    capability(vendor_lookup),
    capability(payment_submission),
    capability(compliance_review),
    capability(ledger_audit)
]).

% Courier: messaging/integration agent — routes pulses between systems
agent(courier, [
    oath(guard_evidence),
    role(courier),
    domain(integration),
    capability(message_routing),
    capability(event_forwarding),
    capability(adapter_sync)
]).

% ========================================
% > COLLABORATION RULES
% ========================================

can_collaborate(A1, A2, Task) :-
    A1 \= A2,
    compatible_oaths(A1, A2, Task),
    \+ conflict_of_interest(A1, A2).

% LedgerLark oversees any accounting task
compatible_oaths(A1, A2, accounting_review) :-
    agent(A1, Attrs1), member(role(overseer), Attrs1),
    agent(A2, Attrs2), member(domain(accounting), Attrs2).

% Clerk + auditor collaborate on ledger tasks
compatible_oaths(A1, A2, ledger_review) :-
    agent(A1, Attrs1), member(domain(accounting), Attrs1),
    agent(A2, Attrs2), member(domain(accounting), Attrs2),
    A1 \= A2.

% Overseer + courier collaborate on integration/routing tasks
compatible_oaths(A1, A2, integration_sync) :-
    agent(A1, Attrs1), member(role(overseer), Attrs1),
    agent(A2, Attrs2), member(domain(integration), Attrs2).

% Conflict detection — only one overseer permitted
conflict_of_interest(A1, A2) :-
    agent(A1, Attrs1), member(role(R), Attrs1),
    agent(A2, Attrs2), member(role(R), Attrs2),
    exclusive_role(R).

exclusive_role(overseer).

% ========================================
% = PERMISSION INFERENCE
% ========================================

has_permission(Agent, Action, _Resource) :-
    agent(Agent, Attrs),
    member(domain(Domain), Attrs),
    action_in_domain(Action, Domain),
    \+ violates_codex(Agent, Action).

% Orchestration actions — overseer only
action_in_domain(modify_memory(_),    orchestration).
action_in_domain(assert_fact(_),      orchestration).
action_in_domain(verify_constraint(_),orchestration).
action_in_domain(store_pattern(_),    orchestration).

% Accounting actions
action_in_domain(approve_payment(_,_),  accounting).
action_in_domain(pay_vendor(_,_),       accounting).
action_in_domain(view_invoice(_),       accounting).
action_in_domain(submit_payment(_),     accounting).
action_in_domain(compliance_check(_),   accounting).
action_in_domain(audit_ledger(_),       accounting).

% Integration actions
action_in_domain(route_message(_),   integration).
action_in_domain(forward_event(_),   integration).
action_in_domain(sync_adapter(_),    integration).

% ========================================
%  CAPABILITY CHECKING
% ========================================

has_capability(Agent, Capability) :-
    agent(Agent, Attrs),
    member(capability(Capability), Attrs).

can_perform(Agent, Task) :-
    required_capability(Task, Capability),
    has_capability(Agent, Capability).

required_capability(invoice_approval,  invoice_approval).
required_capability(vendor_lookup,     vendor_lookup).
required_capability(payment_submission,payment_submission).
required_capability(compliance_review, compliance_review).
required_capability(ledger_audit,      ledger_audit).
required_capability(message_routing,   message_routing).
required_capability(event_forwarding,  event_forwarding).
required_capability(agent_coordination,agent_coordination).
required_capability(codex_enforcement, codex_enforcement).
required_capability(memory_management, memory_management).

% ========================================
% = AGENT QUERIES
% ========================================

% Find all agents with a specific oath
agents_with_oath(Oath, Agents) :-
    findall(A, (agent(A, Attrs), member(oath(Oath), Attrs)), Agents).

% Find all agents capable of a task
agents_for_task(Task, Agents) :-
    findall(A, can_perform(A, Task), Agents).

% Get agent's full profile
agent_profile(Agent, Profile) :-
    agent(Agent, Attrs),
    Profile = agent(Agent, Attrs).

% ========================================
% > TEST QUERIES (Examples)
% ========================================
% ?- can_collaborate(clerk, auditor, ledger_review).
% ?- has_capability(auditor, compliance_review).
% ?- has_permission(clerk, approve_payment(inv_001, 200), accounting).
% ?- agents_with_oath(guard_ledger, Agents).
% ?- can_perform(ledgerlark, agent_coordination).
% ========================================

% End of Agent_Rules.pl
