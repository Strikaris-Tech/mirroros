"""
Codex Verification Engine - Z3 Formal Verification

Provides mathematical proof of compliance (or violation) for agent actions.
Uses Z3 theorem prover to formally verify Codex axioms.

Architecture:
- Fast tier: Prolog only (< 50ms)
- Strict tier: Prolog + Z3 (< 500ms)
- Deferred tier: Async Z3 (background)
"""

import time
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    from z3 import (
        Solver, DeclareSort, Function, IntSort, BoolSort, Const,
        And, Or, Implies, sat, unsat, unknown
    )
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


class VerificationLevel(Enum):
    """Verification tier selection"""
    FAST = "fast"          # Prolog only
    STRICT = "strict"      # Prolog + Z3
    DEFERRED = "deferred"  # Async Z3 (not implemented yet)


class VerificationStatus(Enum):
    """Z3 verification result status"""
    VALID = "VALID"                # SAT: action is compliant
    VIOLATION = "VIOLATION"        # UNSAT: action violates constraints
    UNKNOWN = "UNKNOWN"            # Z3 could not determine (timeout)
    ERROR = "ERROR"                # Z3 not available or crashed
    SKIPPED = "SKIPPED"            # Fast tier, Z3 not invoked


@dataclass
class ProofArtifact:
    """Structured proof artifact for audit trail"""
    status: VerificationStatus
    agent: str
    action: str
    timestamp: str
    latency_ms: float
    z3_result: Optional[str] = None  # sat, unsat, unknown
    proof_core: Optional[List[str]] = None
    witness_model: Optional[Dict[str, Any]] = None
    proof_hash: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "status": self.status.value,
            "agent": self.agent,
            "action": self.action,
            "timestamp": self.timestamp,
            "latency_ms": round(self.latency_ms, 2),
            "z3_result": self.z3_result,
            "proof_core": self.proof_core,
            "witness_model": self.witness_model,
            "proof_hash": self.proof_hash,
            "error": self.error
        }


class CodexVerifier:
    """
    Z3-based formal verification engine for Codex compliance.
    
    Provides mathematical proofs that agent actions comply with
    (or violate) Codex axioms.
    """
    
    def __init__(self):
        self.z3_available = Z3_AVAILABLE
        self.timeout_ms = 5000  # 5 second timeout
        
        if not self.z3_available:
            print("WARNING: Z3 not available. Strict verification will return errors.")
    
    def verify_budget_compliance(
        self,
        agent: str,
        action: str,
        budget_limit: int,
        action_amount: int
    ) -> ProofArtifact:
        """
        Verify budget compliance constraint.
        
        Axiom: ∀ agent, action:
               is_purchase(action) ∧ amount(action) > limit(agent)
               ⟹ violates_budget(agent, action)
        
        Args:
            agent: Agent identifier
            action: Action string (e.g., "purchase(server, 15000)")
            budget_limit: Agent's budget limit
            action_amount: Amount of the purchase
        
        Returns:
            ProofArtifact with verification result and proof
        """
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        if not self.z3_available:
            return ProofArtifact(
                status=VerificationStatus.ERROR,
                agent=agent,
                action=action,
                timestamp=timestamp,
                latency_ms=0,
                error="Z3 not available"
            )
        
        try:
            # Define Z3 domain
            Agent = DeclareSort('Agent')
            Action = DeclareSort('Action')
            
            budget_limit_func = Function('budget_limit', Agent, IntSort())
            action_amount_func = Function('action_amount', Action, IntSort())
            is_purchase = Function('is_purchase', Action, BoolSort())
            violates_budget = Function('violates_budget', Agent, Action, BoolSort())
            
            # Create constants
            agent_const = Const(agent, Agent)
            action_const = Const('action_0', Action)
            
            # Initialize solver
            solver = Solver()
            solver.set("timeout", self.timeout_ms)
            
            # Assert facts
            solver.add(budget_limit_func(agent_const) == budget_limit)
            solver.add(action_amount_func(action_const) == action_amount)
            solver.add(is_purchase(action_const) == True)
            
            # Add budget compliance axiom
            budget_axiom = Implies(
                And(
                    is_purchase(action_const),
                    action_amount_func(action_const) > budget_limit_func(agent_const)
                ),
                violates_budget(agent_const, action_const)
            )
            solver.add(budget_axiom)
            
            # Check for violation by assuming no violation and seeing if it's consistent
            solver.push()  # Save state
            solver.add(violates_budget(agent_const, action_const) == False)
            
            result = solver.check()
            latency_ms = (time.time() - start_time) * 1000
            
            if result == unsat:
                # UNSAT: assuming no violation creates contradiction
                # Therefore, violation MUST occur (proven)
                proof_core = self._extract_proof_core(solver)
                
                # Get positive proof
                solver.pop()
                solver.add(violates_budget(agent_const, action_const) == True)
                positive_result = solver.check()
                
                witness = None
                if positive_result == sat:
                    model = solver.model()
                    witness = {
                        "budget_limit": model.eval(budget_limit_func(agent_const)).as_long(),
                        "action_amount": model.eval(action_amount_func(action_const)).as_long(),
                        "violates_budget": str(model.eval(violates_budget(agent_const, action_const)))
                    }
                
                artifact = ProofArtifact(
                    status=VerificationStatus.VIOLATION,
                    agent=agent,
                    action=action,
                    timestamp=timestamp,
                    latency_ms=latency_ms,
                    z3_result="unsat",
                    proof_core=proof_core,
                    witness_model=witness
                )
                
            elif result == sat:
                # SAT: no violation is consistent with facts
                # Action is compliant (proven)
                model = solver.model()
                witness = {
                    "budget_limit": model.eval(budget_limit_func(agent_const)).as_long(),
                    "action_amount": model.eval(action_amount_func(action_const)).as_long(),
                    "violates_budget": str(model.eval(violates_budget(agent_const, action_const)))
                }
                
                artifact = ProofArtifact(
                    status=VerificationStatus.VALID,
                    agent=agent,
                    action=action,
                    timestamp=timestamp,
                    latency_ms=latency_ms,
                    z3_result="sat",
                    witness_model=witness
                )
                
            else:  # unknown
                artifact = ProofArtifact(
                    status=VerificationStatus.UNKNOWN,
                    agent=agent,
                    action=action,
                    timestamp=timestamp,
                    latency_ms=latency_ms,
                    z3_result="unknown",
                    error="Z3 timeout or resource limit"
                )
            
            # Add proof hash
            artifact.proof_hash = self._compute_proof_hash(artifact)
            
            return artifact
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ProofArtifact(
                status=VerificationStatus.ERROR,
                agent=agent,
                action=action,
                timestamp=timestamp,
                latency_ms=latency_ms,
                error=str(e)
            )
    
    def _extract_proof_core(self, solver: Any) -> List[str]:
        """
        Extract minimal unsatisfiable core from solver.
        
        Returns list of constraint strings that form the contradiction.
        """
        try:
            core = solver.unsat_core()
            return [str(c) for c in core] if core else []
        except Exception:
            return []
    
    def _compute_proof_hash(self, artifact: ProofArtifact) -> str:
        """
        Compute SHA-256 hash of proof artifact for tamper detection.
        
        Hash includes: agent, action, timestamp, z3_result, witness_model
        """
        hash_input = json.dumps({
            "agent": artifact.agent,
            "action": artifact.action,
            "timestamp": artifact.timestamp,
            "z3_result": artifact.z3_result,
            "witness_model": artifact.witness_model
        }, sort_keys=True)
        
        return "sha256:" + hashlib.sha256(hash_input.encode()).hexdigest()[:16]


# Singleton instance for convenience
_verifier_instance = None

def get_verifier() -> CodexVerifier:
    """Get singleton CodexVerifier instance"""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = CodexVerifier()
    return _verifier_instance
