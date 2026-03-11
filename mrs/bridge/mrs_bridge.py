"""
Mirrors Reasoning Stack - Bridge Layer
Connects agents to the Prolog reasoning engine with logging and verification
"""

from pyswip import Prolog
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib
import time

# Z3 formal verification (optional)
try:
    from mrs.verifier.verify_codex import CodexVerifier, VerificationLevel, VerificationStatus
    Z3_VERIFICATION_AVAILABLE = True
except ImportError:
    Z3_VERIFICATION_AVAILABLE = False
    VerificationLevel = None
    VerificationStatus = None

# immudb ledger (optional — MRS operates without it)
try:
    from ledger.immudb_client import MRSLedger
    LEDGER_AVAILABLE = True
except ImportError:
    MRSLedger = None  # type: ignore[misc,assignment]
    LEDGER_AVAILABLE = False


class ConcordanceError(RuntimeError):
    """
    Raised at boot when the Z3-Prolog vocabulary concordance is broken.

    Conditions that trigger this error:
    - prolog/concordance.pl is missing
    - prolog/concordance.pl cannot be loaded by the Prolog engine
    - Any Z3 surface predicate in verifier/essence_runes.py has no
      corresponding entry in concordance.pl

    The system refuses to start. Add the missing entries to
    prolog/concordance.pl and restart. Drift is structurally impossible
    once this gate is passed.
    """
    pass


class MRSBridge:
    """
    Main interface between agents and the MRS reasoning layer.

    Provides:
    - Fact assertion with Codex validation
    - Prolog query execution
    - Inference and reasoning
    - Dual logging (JSON + text)
    """

    def __init__(self, prolog_path: str = "prolog/", memory_path: str = "memory/", ledger: Optional["MRSLedger"] = None):
        self.prolog = Prolog()
        
        # Get MRS root directory (where this file lives)
        mrs_root = Path(__file__).parent.parent
        
        # Use absolute paths relative to MRS root
        self.prolog_path = mrs_root / prolog_path if not Path(prolog_path).is_absolute() else Path(prolog_path)
        self.memory_path = mrs_root / memory_path if not Path(memory_path).is_absolute() else Path(memory_path)

        # Dual logging setup
        self.reasoning_log_path = self.memory_path / "reasoning_log.json"
        self.bridge_log_path = self.memory_path / "bridge.log"
        self.outcomes_log_path = self.memory_path / "outcomes.json"

        # immudb ledger (optional)
        self.ledger = ledger

        # Action ID counter for generating unique IDs
        self._action_counter = 0

        # Ensure memory directory exists
        self.memory_path.mkdir(exist_ok=True)

        # Setup text logging
        logging.basicConfig(
            filename=self.bridge_log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Load core Prolog files
        self._load_prolog_files()

        # Load concordance and verify Z3-Prolog vocabulary alignment
        self._concordance_verified = False
        self._concordance_predicate_count = 0
        self._load_concordance()

        # Initialize Z3 verifier (optional)
        self.verifier = None
        if Z3_VERIFICATION_AVAILABLE:
            try:
                self.verifier = CodexVerifier()
                self.logger.info("Z3 formal verification enabled")
            except Exception as e:
                self.logger.warning(f"Z3 verifier initialization failed: {e}")
        else:
            self.logger.info("Z3 not available - using Prolog-only verification")

        self.logger.info("MRSBridge initialized")

    def _load_prolog_files(self):
        """Load Codex laws and agent rules into Prolog engine"""
        try:
            # Suppress redefinition warnings for testing
            list(self.prolog.query("set_prolog_flag(verbose, silent)"))

            codex_laws = self.prolog_path / "Codex_Laws.pl"
            agent_rules = self.prolog_path / "Agent_Rules.pl"

            if codex_laws.exists():
                # Use list() to consume the generator and catch errors
                posix_path = Path(codex_laws).as_posix()
                list(self.prolog.query(f"consult('{posix_path}')"))
                self.logger.info(f"Loaded {codex_laws}")
            else:
                self.logger.warning(f"Codex laws not found: {codex_laws}")

            if agent_rules.exists():
                posix_agent = Path(agent_rules).as_posix()
                list(self.prolog.query(f"consult('{posix_agent}')"))
                self.logger.info(f"Loaded {agent_rules}")
            else:
                self.logger.warning(f"Agent rules not found: {agent_rules}")

        except Exception as e:
            self.logger.warning(f"Prolog files not loaded (non-fatal): {e}")
            # Don't raise - allow MRS to work without Prolog for JSON logging

    def _load_concordance(self):
        """
        Load prolog/concordance.pl and verify Z3-Prolog vocabulary alignment.

        Called once at boot, immediately after Prolog files are loaded.
        Introspects verifier/essence_runes.py for all declared Z3 Functions,
        then checks that every one has an entry in concordance.pl.

        If concordance.pl is absent or any Z3 predicate lacks a mapping,
        this method raises ConcordanceError — the system will not start.
        Once past this gate, vocabulary drift is structurally impossible.

        Raises:
            ConcordanceError: if concordance.pl is missing, unloadable, or
                if any Z3 surface predicate has no Prolog mapping entry.
        """
        concordance_path = self.prolog_path / "concordance.pl"

        if not concordance_path.exists():
            raise ConcordanceError(
                f"prolog/concordance.pl not found at {concordance_path}. "
                f"The Rune-to-Clause vocabulary map is required at boot. "
                f"See docs/CONCORDANCE_DESIGN.md for the specification."
            )

        try:
            posix_concordance = Path(concordance_path).as_posix()
            list(self.prolog.query(f"consult('{posix_concordance}')"))
            self.logger.info(f"Concordance loaded: {concordance_path}")
        except Exception as e:
            raise ConcordanceError(
                f"Failed to load prolog/concordance.pl: {e}"
            )

        z3_predicates = self._get_z3_surface_predicates()
        self._verify_concordance_coverage(z3_predicates)

        self._concordance_verified = True
        self._concordance_predicate_count = len(z3_predicates)
        self.logger.info(
            f"Concordance verified: {self._concordance_predicate_count} "
            f"Z3 surface predicates mapped"
        )

    def _get_z3_surface_predicates(self) -> List[str]:
        """
        Return the names of all Z3 Function predicates declared in the
        EssenceRunes verifier class.

        These are the surface predicates — the ones that represent facts
        about the world and must have Prolog equivalents in concordance.pl.
        Sorts (DeclareSort results) are excluded; only Function declarations
        are checked.

        Returns:
            List of Z3 Function name strings, or empty list if EssenceRunes
            is not importable (e.g. Z3 not installed).
        """
        names = []
        try:
            from mrs.verifier.essence_runes import EssenceRunes
            from z3 import FuncDeclRef
            er = EssenceRunes()
            for attr_name in dir(er):
                if attr_name.startswith('_'):
                    continue
                val = getattr(er, attr_name, None)
                if isinstance(val, FuncDeclRef):
                    names.append(val.name())
        except ImportError:
            self.logger.warning(
                "verifier/essence_runes.py not importable — "
                "concordance coverage check skipped (Z3 unavailable)"
            )
        return names

    def _verify_concordance_coverage(self, z3_predicates: List[str]):
        """
        Boot-time check: every Z3 surface predicate must have a concordance entry.

        Queries Prolog for each predicate name using the concordance/5 fact.
        Any predicate without an entry is collected; if the missing list is
        non-empty, a ConcordanceError is raised and logged to the reasoning
        log as a VIOLATION.

        Args:
            z3_predicates: List of Z3 Function names from _get_z3_surface_predicates.

        Raises:
            ConcordanceError: if any predicate in z3_predicates has no entry
                in prolog/concordance.pl.
        """
        if not z3_predicates:
            return  # Z3 unavailable; skip check

        missing = []
        for name in z3_predicates:
            safe_name = name.replace("'", "\\'")
            result = list(self.prolog.query(
                f"concordance(z3, '{safe_name}', prolog, _, _)"
            ))
            if not result:
                missing.append(name)

        if missing:
            self._log_reasoning(
                agent="system",
                action="boot_concordance_check",
                status="VIOLATION",
                details={
                    "missing_mappings": missing,
                    "checked_count": len(z3_predicates)
                }
            )
            raise ConcordanceError(
                f"Concordance drift detected at boot — "
                f"{len(missing)} Z3 predicate(s) have no Prolog mapping: "
                f"{missing}. "
                f"Add entries to prolog/concordance.pl and restart."
            )

        self._log_reasoning(
            agent="system",
            action="boot_concordance_check",
            status="VALID",
            details={"verified_count": len(z3_predicates)}
        )

    def _translate_fact_via_concordance(self, fact: str) -> Optional[Dict[str, Any]]:
        """
        Translate a Prolog fact string to its Z3 equivalent via the concordance.

        Uses Prolog's own term_to_atom/2 and functor/3 to parse the fact safely,
        then queries concordance.pl for the Z3 Function name and argument sorts.

        Returns None when the predicate is not in the concordance vocabulary
        (e.g. memory_fact/2, agent/2). These are non-relational operational
        facts; the Z3 structural gate skips them with verdict SKIP.

        Args:
            fact: Prolog fact string, e.g. "owns(ledgerlark, audit_vault)"

        Returns:
            Dict with z3_name, prolog_name, arity, arg_sorts — or None if
            the predicate is not in the concordance vocabulary.
        """
        try:
            safe_fact = fact.replace("'", "\\'")
            parse_result = list(self.prolog.query(
                f"term_to_atom(T, '{safe_fact}'), functor(T, PrologName, Arity)"
            ))
            if not parse_result:
                return None

            prolog_name = str(parse_result[0]['PrologName'])
            arity = int(parse_result[0]['Arity'])

            concordance_result = list(self.prolog.query(
                f"concordance(z3, Z3Name, prolog, {prolog_name}, ArgSorts), "
                f"length(ArgSorts, {arity})"
            ))
            if not concordance_result:
                return None  # Not in vocabulary — Z3 gate skips

            z3_name = str(concordance_result[0]['Z3Name'])
            arg_sorts = [str(s) for s in concordance_result[0]['ArgSorts']]

            return {
                'z3_name': z3_name,
                'prolog_name': prolog_name,
                'arity': arity,
                'arg_sorts': arg_sorts
            }
        except Exception as e:
            self.logger.debug(f"Concordance translation failed for {fact!r}: {e}")
            return None

    def _verify_structural_z3(self, translation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Z3 structural verification on a concordance-translated fact.

        Creates fresh Z3 constants of the appropriate sorts and checks whether
        the claimed predicate is satisfiable with the L1+L2 essence axioms.
        SAT = structurally valid. UNSAT = axiomatically impossible (logic error).

        Vocabulary/arity mismatches are caught before the solver is invoked.
        Sort names not present in EssenceRunes (e.g. 'commitment') return
        UNKNOWN and do not block the assertion.

        Args:
            translation: Dict from _translate_fact_via_concordance.

        Returns:
            Dict with status: VALID | VIOLATION | UNKNOWN | ERROR
        """
        try:
            from mrs.verifier.essence_runes import EssenceRunes
            from z3 import Solver, Const, FuncDeclRef, sat

            er = EssenceRunes()
            sort_map = {
                'agent':    er.Agent,
                'resource': er.Resource,
                'action':   er.Action,
                'domain':   er.Domain,
                'evidence': er.Evidence,
            }

            z3_name = translation['z3_name']
            arg_sorts = translation['arg_sorts']

            # Find the Z3 Function by name
            z3_func = None
            for attr in dir(er):
                if attr.startswith('_'):
                    continue
                val = getattr(er, attr, None)
                if isinstance(val, FuncDeclRef) and val.name() == z3_name:
                    z3_func = val
                    break

            if z3_func is None:
                return {
                    'status': 'UNKNOWN',
                    'reason': f"Z3 Function '{z3_name}' not found in EssenceRunes",
                    'z3_name': z3_name
                }

            # Arity guard
            if z3_func.arity() != len(arg_sorts):
                return {
                    'status': 'VIOLATION',
                    'reason': (
                        f"Arity mismatch: concordance declares {len(arg_sorts)} "
                        f"arg(s) for '{z3_name}' but Z3 Function has {z3_func.arity()}"
                    ),
                    'z3_name': z3_name
                }

            # Resolve sorts — unknown sorts yield UNKNOWN (graceful skip)
            constants = []
            for i, sort_name in enumerate(arg_sorts):
                z3_sort = sort_map.get(sort_name)
                if z3_sort is None:
                    return {
                        'status': 'UNKNOWN',
                        'reason': f"Sort '{sort_name}' not available in EssenceRunes",
                        'z3_name': z3_name
                    }
                constants.append(Const(f'_x{i}', z3_sort))

            # Check satisfiability: can this predicate hold with the L1+L2 axioms?
            solver = Solver()
            solver.set("timeout", 5000)
            for axiom in er.get_essence_axioms():
                solver.add(axiom)
            solver.add(z3_func(*constants) == True)

            check_result = solver.check()
            if check_result == sat:
                return {
                    'status': 'VALID',
                    'z3_name': z3_name,
                    'verified_arity': len(constants)
                }
            else:
                return {
                    'status': 'VIOLATION',
                    'reason': 'Structurally unsatisfiable with L1+L2 axioms',
                    'z3_name': z3_name
                }

        except Exception as e:
            self.logger.warning(f"Z3 structural verification error: {e}")
            return {'status': 'ERROR', 'error': str(e)}

    def load_module(self, module_path: str) -> Dict[str, Any]:
        """
        Load a Prolog module (e.g., compliance rules).

        Args:
            module_path: Path to Prolog file, relative to MRS root or absolute

        Returns:
            Dict with success status and loaded path
        """
        path = Path(module_path)
        if not path.is_absolute():
            mrs_root = Path(__file__).parent.parent
            path = mrs_root / module_path

        if not path.exists():
            self.logger.error(f"Module not found: {path}")
            return {"success": False, "reason": f"File not found: {path}"}

        try:
            posix_module = Path(path).as_posix()
            list(self.prolog.query(f"consult('{posix_module}')"))
            self.logger.info(f"Loaded module: {path}")
            self._log_reasoning(
                agent="system",
                action=f"load_module({module_path})",
                status="ASSERTED",
                details={"module": str(path)}
            )
            return {"success": True, "module": str(path)}
        except Exception as e:
            self.logger.error(f"Failed to load module {path}: {e}")
            return {"success": False, "reason": str(e)}

    def export_audit_trail(self, filename: str) -> Dict[str, Any]:
        """
        Export complete audit trail to a JSON file.

        Args:
            filename: Output filename (written to memory/ directory)

        Returns:
            Dict with success status and export path
        """
        export_path = self.memory_path / filename

        # Collect all audit data
        audit_data = {
            "exported_at": datetime.now().isoformat(),
            "reasoning_log": [],
            "outcomes": []
        }

        if self.reasoning_log_path.exists():
            try:
                with open(self.reasoning_log_path) as f:
                    audit_data["reasoning_log"] = json.load(f)
            except json.JSONDecodeError:
                self.logger.warning("Could not read reasoning log for export")

        if self.outcomes_log_path.exists():
            try:
                with open(self.outcomes_log_path) as f:
                    audit_data["outcomes"] = json.load(f)
            except json.JSONDecodeError:
                self.logger.warning("Could not read outcomes log for export")

        try:
            with open(export_path, 'w') as f:
                json.dump(audit_data, f, indent=2)
            self.logger.info(f"Exported audit trail: {export_path}")
            return {"success": True, "path": str(export_path)}
        except Exception as e:
            self.logger.error(f"Failed to export audit trail: {e}")
            return {"success": False, "reason": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """
        Check MRS health status.

        Returns:
            Dict with health information:
            - prolog_available: Whether Prolog engine is working
            - codex_loaded: Whether Codex laws are loaded
            - concordance_verified: Whether Z3-Prolog vocabulary was verified at boot
            - concordance_predicate_count: Number of Z3 predicates verified
            - error: Error message if any issues detected
        """
        health = {
            "prolog_available": False,
            "codex_loaded": False,
            "concordance_verified": self._concordance_verified,
            "concordance_predicate_count": self._concordance_predicate_count,
            "ledger_available": self.ledger.is_available() if self.ledger is not None else False,
            "error": None
        }

        try:
            # Test basic Prolog functionality with a simple query
            list(self.prolog.query("true"))
            health["prolog_available"] = True

            # Check if Codex laws are loaded by querying for a predicate
            # that should exist in Codex_Laws.pl
            result = list(self.prolog.query("current_predicate(violates_codex/2)"))
            health["codex_loaded"] = len(result) > 0

        except Exception as e:
            health["error"] = str(e)
            self.logger.warning(f"Health check failed: {e}")

        return health

    def _generate_action_id(self) -> str:
        """
        Generate a unique action ID.

        Format: action_YYYYMMDD_NNN
        where NNN is a zero-padded counter
        """
        self._action_counter += 1
        date_str = datetime.now().strftime("%Y%m%d")
        return f"action_{date_str}_{self._action_counter:03d}"

    def _generate_outcome_id(self) -> str:
        """
        Generate a unique outcome ID.

        Format: outcome_YYYYMMDD_NNN
        Uses timestamp + hash for uniqueness
        """
        timestamp = int(time.time() * 1000)  # milliseconds
        hash_input = f"{timestamp}_{self._action_counter}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:3]
        date_str = datetime.now().strftime("%Y%m%d")
        return f"outcome_{date_str}_{hash_suffix}"

    def assert_fact(
        self,
        fact: str,
        agent: Optional[str] = None,
        verification_level: str = "fast"
    ) -> Dict[str, Any]:
        """
        Assert a new fact into the reasoning system through the dual gate.

        Phase C dual-gate flow (when concordance is live and Z3 is available):
          Gate 1 — Prolog behavioral: Does this fact violate any Codex law or oath?
          Gate 2 — Z3 structural: Is this fact structurally valid per L1+L2 axioms?

        Verdicts:
          PERMITTED + VALID   → ASSERTED  (both gates pass)
          PERMITTED + SKIP    → ASSERTED  (non-vocabulary fact; Prolog decides)
          PERMITTED + UNKNOWN → ASSERTED  (Z3 could not determine; Prolog decides)
          PERMITTED + VIOLATION → CONTRADICTION (surfaces as error; not committed)
          REJECTED  + any     → REJECTED  (Prolog is Law; Z3 cannot override)

        When concordance is not yet verified or Z3 is unavailable, falls back
        to Prolog-only verification (backward compatible).

        Args:
            fact: Prolog fact string (e.g., "owns(ledgerlark, audit_vault)")
            agent: Name of agent asserting the fact (for Codex checking)
            verification_level: "fast" | "strict" — controls legacy budget check

        Returns:
            Dict with success, timestamp, action_id, prolog_verdict, z3_verdict
        """
        timestamp = datetime.now().isoformat()
        action_id = self._generate_action_id()

        # ── Gate 1: Prolog behavioral check ──────────────────────────────────
        prolog_violations = self._check_violations(agent, fact) if agent else []
        prolog_verdict = "REJECTED" if prolog_violations else "PERMITTED"

        # ── Gate 2: Z3 structural check via concordance ───────────────────────
        z3_verdict = {"status": "SKIP"}
        if self._concordance_verified and Z3_VERIFICATION_AVAILABLE:
            translation = self._translate_fact_via_concordance(fact)
            if translation is not None:
                z3_verdict = self._verify_structural_z3(translation)

        z3_status = z3_verdict.get("status", "SKIP")

        # ── Contradiction: Prolog permits but Z3 rejects ──────────────────────
        if prolog_verdict == "PERMITTED" and z3_status == "VIOLATION":
            details = {
                "fact": fact,
                "action_id": action_id,
                "prolog_verdict": prolog_verdict,
                "z3_verdict": z3_verdict,
                "contradiction": "Prolog permits but Z3 structural gate rejects"
            }
            self._log_reasoning(
                agent=agent or "system",
                action=f"assert({fact})",
                status="CONTRADICTION",
                details=details
            )
            self.logger.warning(
                f"CONTRADICTION on {fact!r}: Prolog permits, Z3 rejects "
                f"({z3_verdict.get('reason', 'structurally unsatisfiable')})"
            )
            return {
                "success": False,
                "reason": "z3_structural_violation",
                "prolog_verdict": prolog_verdict,
                "z3_verdict": z3_verdict,
                "timestamp": timestamp,
                "action_id": action_id
            }

        # ── Prolog rejected (Prolog is Law) ───────────────────────────────────
        if prolog_verdict == "REJECTED":
            # Legacy strict-mode budget check (preserved for backward compat)
            z3_proof = None
            if verification_level == "strict" and self.verifier and agent:
                z3_proof = self._verify_with_z3(agent, fact)
                if z3_proof and z3_proof.get("status") == "VIOLATION":
                    prolog_violations.append(
                        f"Z3 budget verification: {z3_proof.get('z3_result')}"
                    )

            details = {
                "violations": prolog_violations,
                "action_id": action_id,
                "prolog_verdict": prolog_verdict,
                "z3_verdict": z3_verdict
            }
            if z3_proof:
                details["z3_proof"] = z3_proof

            self._log_reasoning(
                agent=agent or "system",
                action=f"assert({fact})",
                status="REJECTED",
                details=details
            )
            return {
                "success": False,
                "reason": "codex_violation",
                "violations": prolog_violations,
                "prolog_verdict": prolog_verdict,
                "z3_verdict": z3_verdict,
                "timestamp": timestamp,
                "action_id": action_id
            }

        # ── Both gates passed (or Z3 SKIP/UNKNOWN): commit ───────────────────
        try:
            self.logger.debug(f"  Asserting to Prolog: {fact}")
            self.prolog.assertz(fact)
            self.logger.info(f"✓ Asserted: {fact} (by {agent or 'system'})")

            # Legacy strict-mode budget proof (preserved for backward compat)
            z3_proof = None
            if verification_level == "strict" and self.verifier and agent:
                z3_proof = self._verify_with_z3(agent, fact)

            details = {
                "fact": fact,
                "action_id": action_id,
                "prolog_verdict": prolog_verdict,
                "z3_verdict": z3_verdict
            }
            if z3_status not in ("SKIP", "UNKNOWN", "ERROR"):
                details["dual_gate"] = True
            if z3_proof:
                details["z3_proof"] = z3_proof

            self._log_reasoning(
                agent=agent or "system",
                action=f"assert({fact})",
                status="ASSERTED",
                details=details
            )

            result = {
                "success": True,
                "fact": fact,
                "timestamp": timestamp,
                "agent": agent,
                "action_id": action_id,
                "prolog_verdict": prolog_verdict,
                "z3_verdict": z3_verdict
            }
            if z3_proof:
                result["z3_proof"] = z3_proof
            return result

        except Exception as e:
            self.logger.error(f"Assertion failed: {fact} - {e}", exc_info=True)
            return {
                "success": False,
                "reason": str(e),
                "timestamp": timestamp,
                "action_id": action_id
            }

    def query(self, query_str: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Execute a Prolog query and return results.

        Args:
            query_str: Prolog query (e.g., "agent(X, Y)")
            max_results: Maximum number of results to return

        Returns:
            List of result dictionaries
        """
        try:
            results = []
            for i, result in enumerate(self.prolog.query(query_str)):
                if i >= max_results:
                    break
                results.append(result)

            self.logger.info(f"Query executed: {query_str} ({len(results)} results)")
            return results

        except Exception as e:
            self.logger.error(f"Query failed: {query_str} - {e}")
            return []

    def infer(self, agent: str, goal: str) -> List[Dict[str, Any]]:
        """
        Perform inference based on a goal.

        Args:
            agent: Agent performing inference
            goal: Prolog goal to prove

        Returns:
            List of inferred facts
        """
        results = self.query(goal)

        self._log_reasoning(
            agent=agent,
            action=f"infer({goal})",
            status="INFERRED",
            details={
                "goal": goal,
                "results_count": len(results),
                "results": results[:10]  # Log first 10
            }
        )

        return results

    def check_authorization(self, agent: str, action: str, target: str) -> bool:
        """
        Check if agent is authorized to perform action on target.

        Args:
            agent: Agent name
            action: Action to perform
            target: Target resource

        Returns:
            True if authorized, False otherwise
        """
        query = f"can_act({agent}, {action}({target}))"
        results = self.query(query)

        authorized = len(results) > 0

        self.logger.info(
            f"Authorization check: {agent} -> {action}({target}) = {authorized}"
        )

        return authorized

    def _check_violations(self, agent: str, action: str) -> List[str]:
        """Check if action violates Codex laws"""
        violations = []

        # Query for violations
        violation_query = f"violates_codex({agent}, {action})"
        results = self.query(violation_query)

        if results:
            violations.append(f"Action violates Codex: {action}")

        # Check for unauthorized modifications
        unauth_query = f"unauthorized_memory_modification({agent}, _)"
        unauth_results = self.query(unauth_query)

        if unauth_results:
            violations.append("Unauthorized memory modification detected")

        return violations

    def _verify_with_z3(self, agent: str, action: str) -> Optional[Dict[str, Any]]:
        """
        Perform Z3 formal verification on action.
        
        Parses action string and calls appropriate Z3 verifier method.
        Returns proof artifact dictionary or None if verification not applicable.
        """
        if not self.verifier:
            return None
        
        try:
            # Parse action for budget compliance verification
            if "purchase(" in action:
                # Extract purchase amount from action string
                # Format: purchase(item, amount) or purchase(item)
                amount = self._extract_purchase_amount(agent, action)
                budget = self._get_agent_budget_limit(agent)
                
                if amount is not None and budget is not None:
                    proof = self.verifier.verify_budget_compliance(
                        agent=agent,
                        action=action,
                        budget_limit=budget,
                        action_amount=amount
                    )
                    return proof.to_dict()
            
            # Add more verification types here (oath integrity, memory sovereignty, etc.)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Z3 verification failed: {e}")
            return {
                "status": "ERROR",
                "error": str(e),
                "agent": agent,
                "action": action
            }

    def _extract_purchase_amount(self, agent: str, action: str) -> Optional[int]:
        """Extract purchase amount from action string"""
        try:
            # Query Prolog for the action amount
            # This assumes action is something like purchase(item, amount)
            import re
            match = re.search(r'purchase\([^,]+,\s*(\d+)\)', action)
            if match:
                return int(match.group(1))
            return None
        except (ValueError, AttributeError):
            return None

    def _get_agent_budget_limit(self, agent: str) -> Optional[int]:
        """Get agent's budget limit from Prolog"""
        try:
            results = self.query(f"agent_budget_limit({agent}, Limit)")
            if results and len(results) > 0:
                return results[0].get('Limit')
            return None
        except Exception:
            return None

    def _log_reasoning(
        self,
        agent: str,
        action: str,
        status: str,
        details: Dict[str, Any]
    ):
        """Log reasoning step to JSON file"""
        self.logger.debug(f"_log_reasoning called: agent={agent}, action={action}, status={status}")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "status": status,
            "details": details
        }
        self.logger.debug(f"  Log entry: {log_entry}")

        # Load existing logs
        logs = []
        if self.reasoning_log_path.exists():
            try:
                self.logger.debug(f"  Loading existing log from: {self.reasoning_log_path}")
                with open(self.reasoning_log_path) as f:
                    logs = json.load(f)
                self.logger.debug(f"  Loaded {len(logs)} existing entries")
            except json.JSONDecodeError as e:
                self.logger.warning(f"Corrupted reasoning log, starting fresh: {e}")
                logs = []
        else:
            self.logger.debug(f"  Log file doesn't exist yet: {self.reasoning_log_path}")

        # Append new entry
        logs.append(log_entry)
        self.logger.debug(f"  Total entries after append: {len(logs)}")

        # Write back
        try:
            self.logger.debug(f"  Writing to: {self.reasoning_log_path}")
            with open(self.reasoning_log_path, 'w') as f:
                json.dump(logs, f, indent=2)
            self.logger.debug("  ✓ Successfully wrote reasoning log")
        except Exception as e:
            self.logger.error(f"Failed to write reasoning log: {e}", exc_info=True)

        # Seal in immudb (optional — non-blocking, never raises)
        if self.ledger is not None:
            try:
                seal_result = self.ledger.seal(log_entry)
                if seal_result.get("verified"):
                    self.logger.debug(
                        f"  Ledger sealed: {seal_result['key']} tx={seal_result['tx']}"
                    )
            except Exception as e:
                self.logger.warning(f"Ledger seal skipped (non-fatal): {e}")

    def get_reasoning_history(
        self,
        agent: Optional[str] = None,
        limit: int = 50,
        verdicts_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve reasoning history with optional filtering.

        Args:
            agent: Filter by agent name (None for all)
            limit: Maximum entries to return
            verdicts_only: If True, return only entries with dual-gate verdicts
                (status in ASSERTED, REJECTED, CONTRADICTION). Excludes
                operational noise like user_message, agent_response scaffolding.

        Returns:
            List of log entries
        """
        if not self.reasoning_log_path.exists():
            return []

        with open(self.reasoning_log_path) as f:
            logs = json.load(f)

        # Filter by agent if specified
        if agent:
            logs = [log for log in logs if log.get("agent") == agent]

        # Filter to dual-gate verdicts only (excludes operational noise)
        if verdicts_only:
            gate_statuses = {"ASSERTED", "REJECTED", "CONTRADICTION"}
            logs = [
                log for log in logs
                if log.get("status") in gate_statuses
                and "prolog_verdict" in log.get("details", {})
            ]

        # Return most recent entries
        return logs[-limit:]

    def batch_assert(
        self,
        facts: List[str],
        agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assert multiple facts in batch.

        Args:
            facts: List of Prolog fact strings
            agent: Agent asserting facts

        Returns:
            Summary of successes and failures
        """
        results = {
            "total": len(facts),
            "succeeded": 0,
            "failed": 0,
            "violations": []
        }

        for fact in facts:
            result = self.assert_fact(fact, agent)
            if result["success"]:
                results["succeeded"] += 1
            else:
                results["failed"] += 1
                if "violations" in result:
                    results["violations"].extend(result["violations"])

        self.logger.info(
            f"Batch assert completed: {results['succeeded']}/{results['total']} succeeded"
        )

        return results

    def record_outcome(
        self,
        action_id: str,
        expected: str,
        actual: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record the outcome of a previously logged action.

        This enables outcome tracking for reflection and pattern detection.

        Args:
            action_id: ID returned from assert_fact() or other action methods
            expected: Expected outcome description
            actual: Actual outcome that occurred
            success: Whether outcome matched expectation
            metadata: Additional context (error messages, metrics, etc.)

        Returns:
            Dict with success status and outcome_id

        Example:
            action_id = bridge.assert_fact("invoice_approval(ledgerlark, inv_001, approved)", agent="ledgerlark")
            bridge.record_outcome(
                action_id=action_id,
                expected="merge_success",
                actual="merge_failed",
                success=False,
                metadata={"reason": "tests failed", "test_failures": 3}
            )
        """
        outcome_id = self._generate_outcome_id()
        timestamp = datetime.now().isoformat()

        # Find the action type from reasoning log
        action_type = self._get_action_type(action_id)
        agent = self._get_action_agent(action_id)

        # Create outcome entry
        outcome_entry = {
            "outcome_id": outcome_id,
            "action_id": action_id,
            "timestamp": timestamp,
            "agent": agent,
            "action_type": action_type,
            "expected": expected,
            "actual": actual,
            "success": success,
            "metadata": metadata or {}
        }

        # Log to outcomes file
        self._log_outcome(outcome_entry)

        # Link outcome to action in reasoning log
        self._link_outcome_to_action(action_id, outcome_id)

        self.logger.info(
            f"Outcome recorded: {outcome_id} for action {action_id} (success={success})"
        )

        return {
            "success": True,
            "outcome_id": outcome_id,
            "action_id": action_id
        }

    def _get_action_type(self, action_id: str) -> str:
        """Extract action type from action_id's log entry"""
        if not self.reasoning_log_path.exists():
            return "unknown"

        with open(self.reasoning_log_path) as f:
            logs = json.load(f)

        for log in logs:
            if log.get("details", {}).get("action_id") == action_id:
                # Extract type from action string (e.g., "assert(code_review(...))" -> "code_review")
                action_str = log.get("action", "")
                if "(" in action_str:
                    inner = action_str.split("(", 1)[1].split("(")[0]
                    return inner if inner else "unknown"

        return "unknown"

    def _get_action_agent(self, action_id: str) -> str:
        """Extract agent from action_id's log entry"""
        if not self.reasoning_log_path.exists():
            return "unknown"

        with open(self.reasoning_log_path) as f:
            logs = json.load(f)

        for log in logs:
            if log.get("details", {}).get("action_id") == action_id:
                return log.get("agent", "unknown")

        return "unknown"

    def _log_outcome(self, outcome_entry: Dict[str, Any]):
        """Log outcome to outcomes.json"""
        outcomes = []

        if self.outcomes_log_path.exists():
            try:
                with open(self.outcomes_log_path) as f:
                    outcomes = json.load(f)
            except json.JSONDecodeError:
                self.logger.warning("Corrupted outcomes log, starting fresh")
                outcomes = []

        outcomes.append(outcome_entry)

        with open(self.outcomes_log_path, 'w') as f:
            json.dump(outcomes, f, indent=2)

    def _link_outcome_to_action(self, action_id: str, outcome_id: str):
        """Link outcome back to action in reasoning log"""
        if not self.reasoning_log_path.exists():
            return

        with open(self.reasoning_log_path) as f:
            logs = json.load(f)

        # Find and update the action entry
        for log in logs:
            if log.get("details", {}).get("action_id") == action_id:
                if "outcomes" not in log["details"]:
                    log["details"]["outcomes"] = []
                log["details"]["outcomes"].append(outcome_id)
                break

        with open(self.reasoning_log_path, 'w') as f:
            json.dump(logs, f, indent=2)

    def get_outcomes_for_action(self, action_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all outcomes for a given action.

        Args:
            action_id: Action ID to look up

        Returns:
            List of outcome dictionaries
        """
        if not self.outcomes_log_path.exists():
            return []

        with open(self.outcomes_log_path) as f:
            outcomes = json.load(f)

        return [o for o in outcomes if o.get("action_id") == action_id]
