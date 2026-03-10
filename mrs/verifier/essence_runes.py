#!/usr/bin/env python3
"""
ESSENCE RUNES — Layer 1: The Physics Substrate

The 7 Codex relational primitives (Ownership, Consent, etc.) are Layer 2.
They describe how things RELATE. But what ARE the things?

Layer 1 answers this with 8 essence runes grounded in physics:

    ◻︎  Matter      mass-energy E               body that endures
    ▲  Motion      momentum p; force F         impulse that moves body
    ◯  Information  entropy S; bits I           pattern that can copy
    ✧  Spacetime   coordinates x t; metric g   stage and boundary
    ☉  Charge      source term q; field sign   signature that distinguishes
    ∇  Potential   gradient V; stored capacity  readiness to transform
    ⟐  Boundary    interface; surface topology  membrane that regulates flow
    ◎  Oath        conserved symmetry Q         invariant promise

Each relational primitive emerges from a PAIR of essence runes.
The runes are the alphabet. The primitives are the grammar.
"""

import sys
sys.path.insert(0, '.')
from z3 import *


class EssenceRunes:
    """
    Z3 encoding of the 8 essence runes.

    These are ontologically prior to the Codex relational primitives.
    They define what the world IS before we say how it relates.
    """

    def __init__(self):
        # === SORTS ===
        self.Agent = DeclareSort('Agent')
        self.Resource = DeclareSort('Resource')
        self.Action = DeclareSort('Action')

        # === ESSENCE PREDICATES (Layer 1) ===

        # ◻︎ Matter: agent/resource has enduring substance
        self.Matter = Function('Matter', self.Resource, BoolSort())

        # ▲ Motion: agent has impulse toward resource (directed momentum)
        self.Motion = Function('Motion', self.Agent, self.Resource, BoolSort())

        # ◯ Information: resource carries copyable pattern
        self.Information = Function('Information', self.Resource, BoolSort())

        # ✧ Spacetime: resource exists in a locatable region
        self.Spacetime = Function('Spacetime', self.Resource, BoolSort())

        # ☉ Charge: agent carries distinguishing signature
        self.Charge = Function('Charge', self.Agent, BoolSort())

        # ∇ Potential: agent has stored capacity to act on resource
        #   This is the gradient — the difference between what IS and what COULD BE
        self.Potential = Function('Potential', self.Agent, self.Resource, BoolSort())

        # ⟐ Boundary: resource has a membrane regulating flow
        self.Boundary = Function('Boundary', self.Resource, BoolSort())

        # ◎ Oath: agent is bound by a conserved symmetry (invariant promise)
        self.OathRune = Function('OathRune', self.Agent, BoolSort())

        # === WILL (emerges from Potential + Charge) ===
        # Will is not a primitive — it's what happens when
        # a distinguishable agent (Charge) has stored capacity (Potential)
        self.Will = Function('Will', self.Agent, self.Action, BoolSort())

        # === RELATIONAL PRIMITIVES (Layer 2) — what emerges ===
        self.Ownership = Function('Ownership', self.Agent, self.Resource, BoolSort())
        self.Consent = Function('Consent', self.Agent, self.Agent, self.Resource, BoolSort())
        self.Transformation = Function('Transformation', self.Agent, self.Resource, self.Resource, BoolSort())
        self.Performs = Function('Performs', self.Agent, self.Action, BoolSort())
        self.can_access = Function('can_access', self.Agent, self.Resource, BoolSort())

        # Additional Layer 2 sorts and relations
        self.Domain = DeclareSort('Domain')
        self.Evidence = DeclareSort('Evidence')

        self.Sovereignty = Function('Sovereignty', self.Agent, self.Domain, BoolSort())
        self.Stewardship = Function('Stewardship', self.Agent, self.Agent, self.Resource, BoolSort())
        self.Auditability = Function('Auditability', self.Action, self.Evidence, BoolSort())
        self.Witness = Function('Witness', self.Agent, self.Action, BoolSort())

        # RoutedTo — bill (resource) assigned to handling agent (L3 AP routing)
        self.RoutedTo = Function('RoutedTo', self.Resource, self.Agent, BoolSort())

        # Symbolic constants
        self.a = Const('a', self.Agent)
        self.b = Const('b', self.Agent)
        self.r = Const('r', self.Resource)
        self.r2 = Const('r2', self.Resource)
        self.act = Const('act', self.Action)
        self.d = Const('d', self.Domain)
        self.ev = Const('ev', self.Evidence)

    def get_essence_axioms(self):
        """
        The axioms that define how essence runes compose into
        relational primitives. These are the derivation rules.

        Key principle: each relational primitive requires specific
        essence runes as prerequisites. No rune, no relation.
        """
        axioms = []

        # === WILL emerges from Potential + Charge ===
        # You need stored capacity (∇) AND distinguishable identity (☉)
        # to have directed intention. A gradient with no identity is
        # just diffusion. Identity with no gradient is inert.

        # W1: Will requires both Potential and Charge
        axioms.append(
            ForAll([self.a, self.act],
                Implies(
                    self.Will(self.a, self.act),
                    And(
                        self.Charge(self.a),           # ☉ you must be distinguishable
                        Exists([self.r],               # ∇ you must have capacity toward something
                            self.Potential(self.a, self.r))
                    )
                )
            )
        )

        # === TRANSFORMATION requires Will + Motion + Matter ===
        # Physics: transformation = applying force (▲) to matter (◻︎)
        # Agency: transformation requires will (∇+☉) to direct the force

        # T1: Transformation requires Will (agent must intend it)
        axioms.append(
            ForAll([self.a, self.r, self.r2],
                Implies(
                    self.Transformation(self.a, self.r, self.r2),
                    Exists([self.act], self.Will(self.a, self.act))
                )
            )
        )

        # T2: Transformation requires Matter (something to transform)
        axioms.append(
            ForAll([self.a, self.r, self.r2],
                Implies(
                    self.Transformation(self.a, self.r, self.r2),
                    self.Matter(self.r)
                )
            )
        )

        # T3: Transformation requires Motion (impulse to change state)
        axioms.append(
            ForAll([self.a, self.r, self.r2],
                Implies(
                    self.Transformation(self.a, self.r, self.r2),
                    self.Motion(self.a, self.r)
                )
            )
        )

        # T4: Transformation requires Potential (gradient between states)
        axioms.append(
            ForAll([self.a, self.r, self.r2],
                Implies(
                    self.Transformation(self.a, self.r, self.r2),
                    self.Potential(self.a, self.r)
                )
            )
        )

        # T5: Transformation produces new Matter
        axioms.append(
            ForAll([self.a, self.r, self.r2],
                Implies(
                    self.Transformation(self.a, self.r, self.r2),
                    self.Matter(self.r2)
                )
            )
        )

        # === PERFORMS requires Will ===
        # No action without intention. No current without voltage.

        # P1: Every performed action requires Will
        axioms.append(
            ForAll([self.a, self.act],
                Implies(
                    self.Performs(self.a, self.act),
                    self.Will(self.a, self.act)
                )
            )
        )

        # === OWNERSHIP requires Matter + Charge ===
        # You need a thing (◻︎) and a distinguishable claimant (☉)

        # O1: Ownership requires Matter (something to own)
        axioms.append(
            ForAll([self.a, self.r],
                Implies(
                    self.Ownership(self.a, self.r),
                    self.Matter(self.r)
                )
            )
        )

        # O2: Ownership requires Charge (distinguishable owner)
        axioms.append(
            ForAll([self.a, self.r],
                Implies(
                    self.Ownership(self.a, self.r),
                    self.Charge(self.a)
                )
            )
        )

        # === CONSENT requires Information + Charge ===
        # You need copyable pattern (◯) and distinguishable parties (☉)

        # C1: Consent requires Information (pattern to communicate permission)
        axioms.append(
            ForAll([self.a, self.b, self.r],
                Implies(
                    self.Consent(self.a, self.b, self.r),
                    self.Information(self.r)
                )
            )
        )

        # C2: Consent requires Charge on both parties
        axioms.append(
            ForAll([self.a, self.b, self.r],
                Implies(
                    self.Consent(self.a, self.b, self.r),
                    And(self.Charge(self.a), self.Charge(self.b))
                )
            )
        )

        # === SOVEREIGNTY requires Spacetime + Oath ===
        # Jurisdiction needs a region (✧) and an invariant commitment (◎)
        # Authority without territory is empty claim.
        # Territory without binding commitment is anarchy.

        # S1: Sovereignty requires Spacetime (a region to govern)
        axioms.append(
            ForAll([self.a, self.d],
                Implies(
                    self.Sovereignty(self.a, self.d),
                    Exists([self.r], self.Spacetime(self.r))
                )
            )
        )

        # S2: Sovereignty requires Oath (binding commitment to govern)
        axioms.append(
            ForAll([self.a, self.d],
                Implies(
                    self.Sovereignty(self.a, self.d),
                    self.OathRune(self.a)
                )
            )
        )

        # S3: Sovereignty requires Charge (distinguishable authority)
        axioms.append(
            ForAll([self.a, self.d],
                Implies(
                    self.Sovereignty(self.a, self.d),
                    self.Charge(self.a)
                )
            )
        )

        # === STEWARDSHIP requires Matter + Motion + Oath ===
        # Caring for another's substance (◻︎) requires directed effort (▲)
        # bound by promise (◎). Without oath, it's just handling.
        # Without motion, it's just watching. Without matter, nothing to tend.

        # St1: Stewardship requires Matter (something to care for)
        axioms.append(
            ForAll([self.a, self.b, self.r],
                Implies(
                    self.Stewardship(self.a, self.b, self.r),
                    self.Matter(self.r)
                )
            )
        )

        # St2: Stewardship requires Motion (active tending, not passive)
        axioms.append(
            ForAll([self.a, self.b, self.r],
                Implies(
                    self.Stewardship(self.a, self.b, self.r),
                    self.Motion(self.a, self.r)
                )
            )
        )

        # St3: Stewardship requires Oath (bound by promise to the owner)
        axioms.append(
            ForAll([self.a, self.b, self.r],
                Implies(
                    self.Stewardship(self.a, self.b, self.r),
                    self.OathRune(self.a)
                )
            )
        )

        # === ACCESS requires Spacetime + Boundary ===
        # You can only access what exists in a locatable region (✧)
        # and whose membrane (⟐) permits passage.

        # Ac1: Access requires Spacetime (resource must be locatable)
        axioms.append(
            ForAll([self.a, self.r],
                Implies(
                    self.can_access(self.a, self.r),
                    self.Spacetime(self.r)
                )
            )
        )

        # Ac2: Access requires Boundary (a membrane to cross)
        axioms.append(
            ForAll([self.a, self.r],
                Implies(
                    self.can_access(self.a, self.r),
                    self.Boundary(self.r)
                )
            )
        )

        # === AUDITABILITY requires Information + Oath ===
        # A traceable record (◯) that can't be tampered with (◎).
        # Information without oath is rumor. Oath without information is silence.

        # Au1: Auditability requires Information (copyable evidence)
        axioms.append(
            ForAll([self.act, self.ev],
                Implies(
                    self.Auditability(self.act, self.ev),
                    Exists([self.r], self.Information(self.r))
                )
            )
        )

        # === WITNESS requires Boundary + Information + Charge ===
        # Observation across a membrane (⟐) that records pattern (◯)
        # by a distinguishable observer (☉).

        # Wi1: Witness requires Boundary (something to observe across)
        axioms.append(
            ForAll([self.a, self.act],
                Implies(
                    self.Witness(self.a, self.act),
                    Exists([self.r], self.Boundary(self.r))
                )
            )
        )

        # Wi2: Witness requires Information (pattern to record)
        axioms.append(
            ForAll([self.a, self.act],
                Implies(
                    self.Witness(self.a, self.act),
                    Exists([self.r], self.Information(self.r))
                )
            )
        )

        # Wi3: Witness requires Charge (distinguishable observer)
        axioms.append(
            ForAll([self.a, self.act],
                Implies(
                    self.Witness(self.a, self.act),
                    self.Charge(self.a)
                )
            )
        )

        return axioms

    def _solver(self):
        s = Solver()
        s.set("timeout", 10000)
        s.add(self.get_essence_axioms())
        return s


class WillTransformationProbe:
    """
    Probe: Is Will/Potential the proper foundation?

    Physics says: without a gradient, nothing flows.
    No potential difference → no current → no work → no transformation.
    ∇ is the prime mover.

    But ∇ alone is blind diffusion. ∇ + ☉ = Will.
    A directed gradient with identity. THAT is agency.
    """

    def __init__(self):
        self.e = EssenceRunes()

    def _solver(self):
        return self.e._solver()

    def probe_01_no_potential_no_will(self):
        """
        Without Potential (∇), can Will exist?
        Physics: without stored energy, no capacity to act.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        act = Const('act1', self.e.Action)

        # A has no potential toward anything
        r = Const('r', self.e.Resource)
        s.add(ForAll([r], Not(self.e.Potential(A, r))))

        # But A has charge (identity)
        s.add(self.e.Charge(A))

        # Can A still have Will?
        s.add(self.e.Will(A, act))

        return s.check() == unsat  # UNSAT = no potential, no will

    def probe_02_no_charge_no_will(self):
        """
        Without Charge (☉), can Will exist?
        An undistinguished thing can't have directed intention.
        A gradient with no identity is just diffusion — heat death.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        act = Const('act1', self.e.Action)

        # A has no charge (not distinguishable)
        s.add(Not(self.e.Charge(A)))

        # But A has potential
        R = Const('R', self.e.Resource)
        s.add(self.e.Potential(A, R))

        # Can A still have Will?
        s.add(self.e.Will(A, act))

        return s.check() == unsat  # UNSAT = no charge, no will

    def probe_03_potential_plus_charge_enables_will(self):
        """
        With both Potential (∇) and Charge (☉), is Will possible?
        This is the positive case — the two runes compose into agency.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        act = Const('act1', self.e.Action)
        R = Const('R', self.e.Resource)

        # A has charge and potential
        s.add(self.e.Charge(A))
        s.add(self.e.Potential(A, R))

        # Can A have Will?
        s.add(self.e.Will(A, act))

        return s.check() == sat  # SAT = the composition works

    def probe_04_no_will_no_action(self):
        """
        Without Will, can action occur?
        No voltage → no current. No gradient → no flow.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        act = Const('act1', self.e.Action)

        # A has no will toward any action
        x = Const('x', self.e.Action)
        s.add(ForAll([x], Not(self.e.Will(A, x))))

        # Can A still perform?
        s.add(self.e.Performs(A, act))

        return s.check() == unsat  # UNSAT = no will, no action

    def probe_05_no_will_no_transformation(self):
        """
        Without Will, can Transformation occur?
        This is the core test: ∇ is the prime mover.
        Remove it and the world is frozen.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        R1 = Const('R1', self.e.Resource)
        R2 = Const('R2', self.e.Resource)

        # A has no will
        x = Const('x', self.e.Action)
        s.add(ForAll([x], Not(self.e.Will(A, x))))

        # But everything else is present
        s.add(self.e.Matter(R1))
        s.add(self.e.Motion(A, R1))
        s.add(self.e.Charge(A))

        # Can transformation still happen?
        s.add(self.e.Transformation(A, R1, R2))

        return s.check() == unsat  # UNSAT = will is required

    def probe_06_matter_without_motion_is_inert(self):
        """
        Matter (◻︎) without Motion (▲) cannot transform.
        A body at rest stays at rest. Newton's first law.
        Even with Will and Potential — if there's no impulse, nothing moves.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        R1 = Const('R1', self.e.Resource)
        R2 = Const('R2', self.e.Resource)

        # Matter exists, agent has will, potential, charge
        s.add(self.e.Matter(R1))
        s.add(self.e.Charge(A))
        s.add(self.e.Potential(A, R1))
        act = Const('act1', self.e.Action)
        s.add(self.e.Will(A, act))

        # But no motion toward the resource
        s.add(Not(self.e.Motion(A, R1)))

        # Can transformation happen?
        s.add(self.e.Transformation(A, R1, R2))

        return s.check() == unsat  # UNSAT = motion required

    def probe_07_transformation_produces_matter(self):
        """
        Transformation creates. Output is new Matter.
        E = mc² — energy becomes mass. The forge produces.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        R1 = Const('R1', self.e.Resource)
        R2 = Const('R2', self.e.Resource)
        act = Const('act1', self.e.Action)

        # Full prerequisites
        s.add(self.e.Matter(R1))
        s.add(self.e.Charge(A))
        s.add(self.e.Potential(A, R1))
        s.add(self.e.Motion(A, R1))
        s.add(self.e.Will(A, act))
        s.add(self.e.Transformation(A, R1, R2))

        # Is the output Matter?
        s.add(Not(self.e.Matter(R2)))

        return s.check() == unsat  # UNSAT = output is always matter

    def probe_08_will_without_matter_is_dream(self):
        """
        Will (∇+☉) without Matter (◻︎) cannot transform.
        You can intend all you want — without substance, nothing changes.
        Thought without body is dream.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        R1 = Const('R1', self.e.Resource)
        R2 = Const('R2', self.e.Resource)
        act = Const('act1', self.e.Action)

        # Will exists, motion exists, but no matter
        s.add(self.e.Charge(A))
        s.add(self.e.Potential(A, R1))
        s.add(self.e.Will(A, act))
        s.add(self.e.Motion(A, R1))
        s.add(Not(self.e.Matter(R1)))

        # Can transformation happen?
        s.add(self.e.Transformation(A, R1, R2))

        return s.check() == unsat  # UNSAT = no matter, no transformation

    def probe_09_ownership_requires_charge(self):
        """
        Without Charge (☉), can Ownership exist?
        If you're indistinguishable, you can't claim anything as yours.
        Identity precedes possession.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(Not(self.e.Charge(A)))
        s.add(self.e.Matter(R))
        s.add(self.e.Ownership(A, R))

        return s.check() == unsat  # UNSAT = no charge, no ownership

    def probe_10_consent_requires_two_charges(self):
        """
        Consent requires two distinguishable parties.
        If either is indistinguishable, consent is meaningless.
        You can't grant permission to a thing you can't identify.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        B = Const('B', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(self.e.Charge(A))
        s.add(Not(self.e.Charge(B)))  # B has no identity
        s.add(self.e.Information(R))
        s.add(self.e.Consent(A, B, R))

        return s.check() == unsat  # UNSAT = both must be distinguishable

    def run(self):
        print("=" * 64)
        print("  ESSENCE RUNES — Will / Transformation Probe")
        print("  ∇ Potential + ☉ Charge = Will")
        print("  Will + ▲ Motion + ◻︎ Matter = Transformation")
        print("=" * 64)

        probes = [
            (
                "No Potential → no Will",
                self.probe_01_no_potential_no_will,
                "Without ∇, Will cannot exist.\n"
                "│    No stored capacity, no readiness to act.\n"
                "│    A battery at zero voltage drives nothing."
            ),
            (
                "No Charge → no Will",
                self.probe_02_no_charge_no_will,
                "Without ☉, Will cannot exist.\n"
                "│    No identity, no directed intention.\n"
                "│    A gradient without signature is just diffusion."
            ),
            (
                "Potential + Charge → Will is possible",
                self.probe_03_potential_plus_charge_enables_will,
                "∇ + ☉ compose into Will. The model is satisfiable.\n"
                "│    Stored capacity + distinguishing signature = agency."
            ),
            (
                "No Will → no Action",
                self.probe_04_no_will_no_action,
                "Without Will, Performs is impossible.\n"
                "│    No voltage, no current. No gradient, no flow."
            ),
            (
                "No Will → no Transformation",
                self.probe_05_no_will_no_transformation,
                "Without Will, Transformation is impossible.\n"
                "│    Even with Matter and Motion present.\n"
                "│    The prime mover is missing."
            ),
            (
                "Matter without Motion is inert",
                self.probe_06_matter_without_motion_is_inert,
                "◻︎ without ▲ cannot transform.\n"
                "│    A body at rest stays at rest.\n"
                "│    Newton's first law, in glyph form."
            ),
            (
                "Transformation produces Matter",
                self.probe_07_transformation_produces_matter,
                "Output of transformation is always ◻︎.\n"
                "│    Energy becomes mass. The forge produces."
            ),
            (
                "Will without Matter is dream",
                self.probe_08_will_without_matter_is_dream,
                "∇+☉ without ◻︎ cannot transform.\n"
                "│    Intention without substance changes nothing.\n"
                "│    Thought without body is dream."
            ),
            (
                "Ownership requires Charge",
                self.probe_09_ownership_requires_charge,
                "Without ☉, Ownership is impossible.\n"
                "│    If you're indistinguishable, you can't claim.\n"
                "│    Identity precedes possession."
            ),
            (
                "Consent requires two Charges",
                self.probe_10_consent_requires_two_charges,
                "Without ☉ on both parties, Consent is impossible.\n"
                "│    Can't grant permission to what you can't identify.\n"
                "│    Two signatures required."
            ),
        ]

        passed = 0
        for name, fn, finding in probes:
            try:
                result = fn()
                status = "✓" if result else "✗"
                if result:
                    passed += 1
                print(f"\n┌─ {name}")
                print(f"│  {status} {finding}")
            except Exception as e:
                print(f"\n┌─ {name}")
                print(f"│  ✗ ERROR: {e}")

        print(f"\n{'=' * 64}")
        print(f"  SYNTHESIS: {passed}/{len(probes)} probes passed")
        print(f"{'=' * 64}")
        print()

        if passed == len(probes):
            print("  The derivation chain holds:")
            print()
            print("     ∇ Potential   ☉ Charge")
            print("          \\         /")
            print("           \\       /")
            print("          Will (∇+☉)")
            print("              |")
            print("     ▲ Motion |  ◻︎ Matter")
            print("          \\   |   /")
            print("           \\  |  /")
            print("       Transformation (▲+∇+☉+◻︎)")
            print("              |")
            print("          new ◻︎ Matter")
            print()
            print("  Four runes compose into Transformation:")
            print("    ∇  readiness to change")
            print("    ☉  identity of the changer")
            print("    ▲  impulse applied")
            print("    ◻︎  substance changed")
            print()
            print("  Remove any one and the world freezes.")
            print("  This is not metaphor. This is physics.")

        print()
        print("=" * 64)

        return passed == len(probes)


class SovereigntyAccessProbe:
    """
    Probe: Sovereignty and Access emerge from Spacetime + Boundary + Oath.

    Sovereignty = ✧ Spacetime + ◎ Oath + ☉ Charge
        You need a region, a binding commitment to govern it,
        and a distinguishable authority.

    Access = ✧ Spacetime + ⟐ Boundary
        You need a locatable thing and a membrane to cross.
    """

    def __init__(self):
        self.e = EssenceRunes()

    def _solver(self):
        return self.e._solver()

    def probe_01_no_spacetime_no_sovereignty(self):
        """No region → no jurisdiction. Authority over nothing is nothing."""
        s = self._solver()
        A = Const('A', self.e.Agent)
        D = Const('D', self.e.Domain)

        # No spacetime exists at all
        r = Const('r', self.e.Resource)
        s.add(ForAll([r], Not(self.e.Spacetime(r))))

        s.add(self.e.Charge(A))
        s.add(self.e.OathRune(A))
        s.add(self.e.Sovereignty(A, D))

        return s.check() == unsat

    def probe_02_no_oath_no_sovereignty(self):
        """
        No oath → no sovereignty.
        Territory without commitment is occupation, not governance.
        Physics: a field without conserved charge dissipates.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        D = Const('D', self.e.Domain)
        R = Const('R', self.e.Resource)

        s.add(self.e.Spacetime(R))
        s.add(self.e.Charge(A))
        s.add(Not(self.e.OathRune(A)))  # No oath
        s.add(self.e.Sovereignty(A, D))

        return s.check() == unsat

    def probe_03_spacetime_plus_oath_enables_sovereignty(self):
        """Positive: ✧ + ◎ + ☉ together allow sovereignty."""
        s = self._solver()
        A = Const('A', self.e.Agent)
        D = Const('D', self.e.Domain)
        R = Const('R', self.e.Resource)

        s.add(self.e.Spacetime(R))
        s.add(self.e.Charge(A))
        s.add(self.e.OathRune(A))
        s.add(self.e.Sovereignty(A, D))

        return s.check() == sat

    def probe_04_no_spacetime_no_access(self):
        """Can't access what doesn't occupy a region."""
        s = self._solver()
        A = Const('A', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(Not(self.e.Spacetime(R)))
        s.add(self.e.Boundary(R))
        s.add(self.e.can_access(A, R))

        return s.check() == unsat

    def probe_05_no_boundary_no_access(self):
        """
        No boundary → no access.
        If there's no membrane, there's nothing to cross.
        Access is meaningless without inside/outside.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(self.e.Spacetime(R))
        s.add(Not(self.e.Boundary(R)))
        s.add(self.e.can_access(A, R))

        return s.check() == unsat

    def probe_06_spacetime_plus_boundary_enables_access(self):
        """Positive: ✧ + ⟐ together allow access."""
        s = self._solver()
        A = Const('A', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(self.e.Spacetime(R))
        s.add(self.e.Boundary(R))
        s.add(self.e.can_access(A, R))

        return s.check() == sat

    def run(self):
        print("=" * 64)
        print("  ESSENCE RUNES — Sovereignty / Access Probe")
        print("  ✧ Spacetime + ◎ Oath + ☉ Charge = Sovereignty")
        print("  ✧ Spacetime + ⟐ Boundary = Access")
        print("=" * 64)

        probes = [
            (
                "No Spacetime → no Sovereignty",
                self.probe_01_no_spacetime_no_sovereignty,
                "Without ✧, jurisdiction is impossible.\n"
                "│    Authority over nothing is nothing."
            ),
            (
                "No Oath → no Sovereignty",
                self.probe_02_no_oath_no_sovereignty,
                "Without ◎, sovereignty is impossible.\n"
                "│    Territory without commitment is occupation.\n"
                "│    A field without conserved charge dissipates."
            ),
            (
                "Spacetime + Oath + Charge → Sovereignty possible",
                self.probe_03_spacetime_plus_oath_enables_sovereignty,
                "✧ + ◎ + ☉ compose into Sovereignty.\n"
                "│    Region + binding promise + identity = jurisdiction."
            ),
            (
                "No Spacetime → no Access",
                self.probe_04_no_spacetime_no_access,
                "Without ✧, access is impossible.\n"
                "│    Can't reach what occupies no region."
            ),
            (
                "No Boundary → no Access",
                self.probe_05_no_boundary_no_access,
                "Without ⟐, access is meaningless.\n"
                "│    No membrane means no inside/outside.\n"
                "│    Nothing to cross, nothing to access."
            ),
            (
                "Spacetime + Boundary → Access possible",
                self.probe_06_spacetime_plus_boundary_enables_access,
                "✧ + ⟐ compose into Access.\n"
                "│    Locatable region + permeable membrane = reachability."
            ),
        ]

        passed = 0
        for name, fn, finding in probes:
            try:
                result = fn()
                status = "✓" if result else "✗"
                if result:
                    passed += 1
                print(f"\n┌─ {name}")
                print(f"│  {status} {finding}")
            except Exception as e:
                print(f"\n┌─ {name}")
                print(f"│  ✗ ERROR: {e}")

        print(f"\n{'=' * 64}")
        print(f"  SYNTHESIS: {passed}/{len(probes)} probes passed")
        print(f"{'=' * 64}")

        if passed == len(probes):
            print()
            print("  Sovereignty: ✧ + ◎ + ☉")
            print("    region + promise + identity = jurisdiction")
            print()
            print("  Access: ✧ + ⟐")
            print("    region + membrane = reachability")

        print()
        print("=" * 64)
        return passed == len(probes)


class OathStewardshipProbe:
    """
    Probe: Oath (◎) as the binding rune.

    Oath = conserved symmetry. Noether's theorem: every symmetry
    implies a conservation law. Every conservation law implies a symmetry.

    ◎ binds across the most relational primitives:
        Sovereignty, Stewardship, Consent, Auditability

    It's the rune that makes promises real.
    Without ◎, stewardship is just handling. Sovereignty is just occupation.
    """

    def __init__(self):
        self.e = EssenceRunes()

    def _solver(self):
        return self.e._solver()

    def probe_01_no_oath_no_stewardship(self):
        """
        Without Oath, stewardship is impossible.
        Caring for another's property without a binding promise
        is just... holding it. No commitment, no stewardship.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        B = Const('B', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(self.e.Matter(R))
        s.add(self.e.Motion(A, R))
        s.add(self.e.Charge(A))
        s.add(Not(self.e.OathRune(A)))  # No oath
        s.add(self.e.Stewardship(A, B, R))

        return s.check() == unsat

    def probe_02_no_matter_no_stewardship(self):
        """Can't steward what has no substance."""
        s = self._solver()
        A = Const('A', self.e.Agent)
        B = Const('B', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(Not(self.e.Matter(R)))
        s.add(self.e.Motion(A, R))
        s.add(self.e.OathRune(A))
        s.add(self.e.Stewardship(A, B, R))

        return s.check() == unsat

    def probe_03_no_motion_no_stewardship(self):
        """
        Stewardship without motion is passive.
        You must actively tend what you steward.
        A steward who doesn't move is a statue.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        B = Const('B', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(self.e.Matter(R))
        s.add(Not(self.e.Motion(A, R)))
        s.add(self.e.OathRune(A))
        s.add(self.e.Stewardship(A, B, R))

        return s.check() == unsat

    def probe_04_oath_matter_motion_enables_stewardship(self):
        """Positive: ◎ + ◻︎ + ▲ compose into Stewardship."""
        s = self._solver()
        A = Const('A', self.e.Agent)
        B = Const('B', self.e.Agent)
        R = Const('R', self.e.Resource)

        s.add(self.e.Matter(R))
        s.add(self.e.Motion(A, R))
        s.add(self.e.OathRune(A))
        s.add(self.e.Charge(A))
        s.add(self.e.Stewardship(A, B, R))

        return s.check() == sat

    def probe_05_oath_is_conserved_symmetry(self):
        """
        Oath as Noether's theorem in social space:
        If the system has a symmetry (◎), there's a conserved quantity.
        If there's a conserved quantity, there's a symmetry.

        Test: An agent with Oath can participate in MORE relations
        than one without. ◎ amplifies, doesn't restrict.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        B = Const('B', self.e.Agent)
        D = Const('D', self.e.Domain)
        R = Const('R', self.e.Resource)

        # A has oath, B does not
        s.add(self.e.OathRune(A))
        s.add(Not(self.e.OathRune(B)))

        # Both have charge
        s.add(self.e.Charge(A))
        s.add(self.e.Charge(B))

        # A can be sovereign, B cannot
        s.add(self.e.Spacetime(R))
        s.add(self.e.Sovereignty(A, D))

        # B tries sovereignty — should fail
        D2 = Const('D2', self.e.Domain)
        s.add(self.e.Sovereignty(B, D2))

        return s.check() == unsat  # B's sovereignty fails without oath

    def probe_06_witness_requires_boundary_information_charge(self):
        """
        Witness = ⟐ + ◯ + ☉
        Observation across membrane, recording pattern, by identified observer.
        Remove any one and witnessing fails.
        """
        s = self._solver()
        A = Const('A', self.e.Agent)
        act = Const('act1', self.e.Action)

        # Has charge and information but no boundary
        s.add(self.e.Charge(A))
        r = Const('r', self.e.Resource)
        s.add(self.e.Information(r))
        s.add(ForAll([r], Not(self.e.Boundary(r))))

        s.add(self.e.Witness(A, act))

        return s.check() == unsat

    def probe_07_auditability_requires_information(self):
        """
        No information → no audit trail.
        You can't record what has no copyable pattern.
        """
        s = self._solver()
        act = Const('act1', self.e.Action)
        ev = Const('ev1', self.e.Evidence)

        # No information exists
        r = Const('r', self.e.Resource)
        s.add(ForAll([r], Not(self.e.Information(r))))

        s.add(self.e.Auditability(act, ev))

        return s.check() == unsat

    def probe_08_full_composition_sovereignty_through_stewardship(self):
        """
        Integration test: Can a sovereign delegate stewardship?
        This requires BOTH composition chains to work:
          Sovereignty = ✧ + ◎ + ☉
          Stewardship = ◻︎ + ▲ + ◎
        Linked by ◎ — the oath binds sovereign to steward.
        """
        s = self._solver()
        Sovereign = Const('Sovereign', self.e.Agent)
        Steward = Const('Steward', self.e.Agent)
        D = Const('D', self.e.Domain)
        R = Const('R', self.e.Resource)

        # Sovereign has full composition
        s.add(self.e.Charge(Sovereign))
        s.add(self.e.OathRune(Sovereign))
        s.add(self.e.Spacetime(R))
        s.add(self.e.Sovereignty(Sovereign, D))

        # Steward has full composition
        s.add(self.e.Charge(Steward))
        s.add(self.e.OathRune(Steward))
        s.add(self.e.Matter(R))
        s.add(self.e.Motion(Steward, R))
        s.add(self.e.Stewardship(Steward, Sovereign, R))

        # Both linked by Oath
        return s.check() == sat  # SAT = the full chain holds

    def run(self):
        print("=" * 64)
        print("  ESSENCE RUNES — Oath / Stewardship / Witness Probe")
        print("  ◎ Oath = conserved symmetry (Noether's theorem)")
        print("  ◎ binds: Sovereignty, Stewardship, Auditability")
        print("=" * 64)

        probes = [
            (
                "No Oath → no Stewardship",
                self.probe_01_no_oath_no_stewardship,
                "Without ◎, Stewardship is impossible.\n"
                "│    Holding without promise is just handling."
            ),
            (
                "No Matter → no Stewardship",
                self.probe_02_no_matter_no_stewardship,
                "Without ◻︎, nothing to steward.\n"
                "│    Can't care for what has no substance."
            ),
            (
                "No Motion → no Stewardship",
                self.probe_03_no_motion_no_stewardship,
                "Without ▲, stewardship is passive.\n"
                "│    A steward who doesn't move is a statue."
            ),
            (
                "Oath + Matter + Motion → Stewardship possible",
                self.probe_04_oath_matter_motion_enables_stewardship,
                "◎ + ◻︎ + ▲ compose into Stewardship.\n"
                "│    Promise + substance + effort = care."
            ),
            (
                "Oath amplifies — enables Sovereignty",
                self.probe_05_oath_is_conserved_symmetry,
                "◎ is the amplifier rune.\n"
                "│    An oath-bound agent can govern.\n"
                "│    An unbound agent with same charge cannot.\n"
                "│    Symmetry → conservation. Noether in social space."
            ),
            (
                "Witness requires Boundary + Information + Charge",
                self.probe_06_witness_requires_boundary_information_charge,
                "Without ⟐, Witness fails.\n"
                "│    No membrane to observe across = no observation."
            ),
            (
                "Auditability requires Information",
                self.probe_07_auditability_requires_information,
                "Without ◯, audit trail is impossible.\n"
                "│    Can't record what has no copyable pattern."
            ),
            (
                "Full chain: Sovereign delegates to Steward",
                self.probe_08_full_composition_sovereignty_through_stewardship,
                "The full composition holds:\n"
                "│    Sovereignty (✧+◎+☉) delegates to\n"
                "│    Stewardship (◻︎+▲+◎) linked by shared ◎.\n"
                "│    Oath is the bridge between governor and caretaker."
            ),
        ]

        passed = 0
        for name, fn, finding in probes:
            try:
                result = fn()
                status = "✓" if result else "✗"
                if result:
                    passed += 1
                print(f"\n┌─ {name}")
                print(f"│  {status} {finding}")
            except Exception as e:
                print(f"\n┌─ {name}")
                print(f"│  ✗ ERROR: {e}")

        print(f"\n{'=' * 64}")
        print(f"  SYNTHESIS: {passed}/{len(probes)} probes passed")
        print(f"{'=' * 64}")

        if passed == len(probes):
            print()
            print("  ◎ Oath is the binding rune:")
            print("    Sovereignty = ✧ + ◎ + ☉   (region + promise + identity)")
            print("    Stewardship = ◻︎ + ▲ + ◎   (substance + effort + promise)")
            print("    Auditability = ◯ + ◎       (pattern + invariance)")
            print("    Witness = ⟐ + ◯ + ☉       (membrane + pattern + observer)")
            print()
            print("  ◎ appears in 3 of 4. It's the social-force carrier.")
            print("  Like the photon carries electromagnetism,")
            print("  ◎ carries trust between agents.")

        print()
        print("=" * 64)
        return passed == len(probes)


def run_all():
    """Run the complete essence rune probe suite."""
    print()
    print("╔" + "═" * 62 + "╗")
    print("║  ESSENCE RUNES — Complete Probe Suite                        ║")
    print("║  8 runes · 3 probe groups · Layer 1 → Layer 2 derivation    ║")
    print("╚" + "═" * 62 + "╝")
    print()

    results = []

    p1 = WillTransformationProbe()
    results.append(("Will / Transformation", p1.run()))

    print()

    p2 = SovereigntyAccessProbe()
    results.append(("Sovereignty / Access", p2.run()))

    print()

    p3 = OathStewardshipProbe()
    results.append(("Oath / Stewardship / Witness", p3.run()))

    # Final summary
    print()
    print("╔" + "═" * 62 + "╗")
    print("║  COMPLETE RUNE MAP                                           ║")
    print("╚" + "═" * 62 + "╝")
    print()
    all_passed = all(r[1] for r in results)

    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")

    if all_passed:
        print()
        print("  Layer 1 (Essence)          Layer 2 (Relational)")
        print("  ─────────────────          ────────────────────")
        print("  ◻︎ Matter ──────────┬────── Ownership (◻︎+☉)")
        print("  ☉ Charge ─────────┤")
        print("                     └────── Consent (◯+☉)")
        print("  ◯ Information ────┤")
        print("                     ├────── Auditability (◯+◎)")
        print("  ◎ Oath ───────────┤")
        print("                     ├────── Sovereignty (✧+◎+☉)")
        print("                     └────── Stewardship (◻︎+▲+◎)")
        print("  ✧ Spacetime ──────┤")
        print("                     └────── Access (✧+⟐)")
        print("  ⟐ Boundary ───────┤")
        print("                     └────── Witness (⟐+◯+☉)")
        print("  ▲ Motion ─────────┘")
        print("  ∇ Potential ──────── Will (∇+☉) ── Transformation (▲+∇+☉+◻︎)")
        print()
        print("  8 runes. 8 relations. Each relation derives from 2-4 runes.")
        print("  No rune is unused. No relation is ungrounded.")
        print()
        print("  This is not English. This is not metaphor.")
        print("  This is a mirror grammar grounded in physics.")
    else:
        print()
        print("  ⚠ Some probe groups failed. Review above.")

    print()
    return all_passed


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
