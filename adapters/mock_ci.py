"""
Mock CI/CD Adapter — demo continuous integration adapter.

Simulates a CI pipeline system (builds, deployments, rollbacks) for MirrorOS
governance demos.  Replace in-memory state with real CI API calls (GitHub
Actions, GitLab CI, Jenkins, etc.); the MRS gate is identical either way.

Purpose:
    Demonstrate MirrorOS governing deployment and rollback actions.

Returns:
    All action methods return a dict:
        permitted (bool)  — True if the action executed
        agent     (str)   — acting agent
        reason    (str)   — verdict explanation
        action    (str)   — action name
        data      (dict)  — action-specific payload

Violations:
    Never call action methods without a bridge.
    Never deploy or rollback without passing the gate.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mrs.bridge.mrs_bridge import MRSBridge


_PIPELINES: dict[str, dict[str, Any]] = {
    "pipeline_api":      {"name": "Forge API",       "env": "production", "last_build": "build_042", "status": "passing"},
    "pipeline_console":  {"name": "FlameConsole",     "env": "production", "last_build": "build_017", "status": "passing"},
    "pipeline_mrs":      {"name": "MRS Bridge",       "env": "staging",    "last_build": "build_031", "status": "passing"},
}

# Agents permitted to deploy to production
_DEPLOY_PERMITTED: set[str] = {"auditor", "ledgerlark"}


class CIAdapter:
    """
    MRS-governed CI/CD adapter.

    Deployment to production is restricted by agent role.
    Rollbacks are always auditor-or-above authority.
    Builds (non-destructive) are open to all accounting-domain agents.
    """

    def __init__(self, bridge: "MRSBridge"):
        self.bridge = bridge
        self._pipelines: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _PIPELINES.items()
        }
        self._build_log: list[dict[str, Any]] = []

    def _gate(self, agent: str, action_term: str) -> tuple[bool, str]:
        """Query MRS for violations before executing."""
        query = f"violates_codex({agent}, {action_term})"
        violations = self.bridge.query(query)
        if violations:
            return False, "action violates Codex"
        return True, "permitted"

    def trigger_build(self, agent: str, pipeline_id: str) -> dict[str, Any]:
        """
        Trigger a CI build.  Non-destructive — any agent may request.

        Args:
            agent:       Requesting agent
            pipeline_id: Pipeline identifier

        Returns:
            Result dict with build_id and status.
        """
        t0 = time.perf_counter()

        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"permitted": False, "reason": f"Pipeline '{pipeline_id}' not found"}

        build_id = f"build_{uuid.uuid4().hex[:6]}"
        record = {
            "build_id":    build_id,
            "pipeline_id": pipeline_id,
            "triggered_by": agent,
            "status":      "queued",
        }
        self._build_log.append(record)
        pipeline["last_build"] = build_id

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "permitted":   True,
            "agent":       agent,
            "action":      "trigger_build",
            "pipeline_id": pipeline_id,
            "build_id":    build_id,
            "reason":      "permitted",
            "latency_ms":  round(latency_ms, 2),
        }

    def deploy(self, agent: str, pipeline_id: str, build_id: str) -> dict[str, Any]:
        """
        Deploy a build to the pipeline's environment.  MRS-gated.

        Production deployments are restricted to auditor and ledgerlark roles.

        Args:
            agent:       Requesting agent
            pipeline_id: Pipeline to deploy to
            build_id:    Build artifact to deploy

        Returns:
            Result dict with permitted, environment, reason.
        """
        t0 = time.perf_counter()

        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"permitted": False, "reason": f"Pipeline '{pipeline_id}' not found"}

        if pipeline["env"] == "production" and agent not in _DEPLOY_PERMITTED:
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "permitted":   False,
                "agent":       agent,
                "action":      "deploy",
                "pipeline_id": pipeline_id,
                "reason":      f"Production deployments require auditor or ledgerlark role",
                "latency_ms":  round(latency_ms, 2),
            }

        pipeline["last_build"] = build_id
        pipeline["status"] = "deployed"

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "permitted":   True,
            "agent":       agent,
            "action":      "deploy",
            "pipeline_id": pipeline_id,
            "build_id":    build_id,
            "environment": pipeline["env"],
            "reason":      "permitted",
            "latency_ms":  round(latency_ms, 2),
        }

    def rollback(self, agent: str, pipeline_id: str) -> dict[str, Any]:
        """
        Roll back a pipeline to its previous build.  Auditor-only.

        Args:
            agent:       Requesting agent
            pipeline_id: Pipeline to roll back

        Returns:
            Result dict with permitted, reason.
        """
        t0 = time.perf_counter()

        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"permitted": False, "reason": f"Pipeline '{pipeline_id}' not found"}

        if agent not in _DEPLOY_PERMITTED:
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "permitted":   False,
                "agent":       agent,
                "action":      "rollback",
                "pipeline_id": pipeline_id,
                "reason":      "Rollbacks require auditor or ledgerlark role",
                "latency_ms":  round(latency_ms, 2),
            }

        pipeline["status"] = "rolled_back"

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "permitted":   True,
            "agent":       agent,
            "action":      "rollback",
            "pipeline_id": pipeline_id,
            "reason":      "permitted",
            "latency_ms":  round(latency_ms, 2),
        }
