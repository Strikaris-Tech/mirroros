"""
Agent Loader - Load agent configurations, prompts, and learned patterns
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class AgentLoader:
    """Load and manage agent configurations"""

    def __init__(self, base_path: str = ".."):
        self.base_path = Path(base_path)

    def load_agent(self, agent_name: str, forge_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load complete agent configuration including learned patterns.

        Args:
            agent_name: Name of the agent (e.g., "ledgerlark")
            forge_config: Forge configuration dict

        Returns:
            Dict with agent identity, prompts, and learned patterns
        """
        if agent_name not in forge_config.get("agents", {}):
            raise ValueError(f"Agent '{agent_name}' not found in forge configuration")

        agent_config = forge_config["agents"][agent_name]

        # Load base configuration
        config_path = self.base_path / agent_config["config_path"]
        with open(config_path, "r") as f:
            base_config = json.load(f)

        # Load prompt template
        prompt_path = self.base_path / agent_config["prompt_template_path"]
        with open(prompt_path, "r") as f:
            prompt_template = f.read()

        # Load learned rules (Prolog)
        learned_rules = self._load_learned_rules(agent_config.get("learned_rules_path"))

        # Load learned focus areas (JSON)
        learned_focus = self._load_learned_focus(agent_config.get("learned_focus_path"))

        # Load MRS context if this agent has MRS access
        mrs_context = None
        if base_config.get("metadata", {}).get("mrs_integrated"):
            mrs_context = self._load_mrs_context(agent_name)

        # Construct system prompt
        system_prompt = self._build_system_prompt(
            agent_config.get("system_prompt_prefix", ""),
            prompt_template,
            learned_focus,
            agent_name=agent_name,
            mrs_context=mrs_context
        )

        return {
            "name": agent_name,
            "display_name": agent_config.get("display_name", agent_name),
            "role": agent_config.get("role", "Agent"),
            "backend": agent_config.get("backend", "openrouter"),
            "model": agent_config.get("model"),
            "fallback_backend": agent_config.get("fallback_backend"),
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_tokens", 2000),
            "tool_calling": agent_config.get("tool_calling", False),
            "system_prompt": system_prompt,
            "base_config": base_config,
            "learned_rules": learned_rules,
            "learned_focus": learned_focus,
        }

    def _load_learned_rules(self, rules_path: Optional[str]) -> str:
        """Load Prolog learned rules"""
        if not rules_path:
            return ""

        full_path = self.base_path / rules_path
        if not full_path.exists():
            return ""

        with open(full_path, "r") as f:
            return f.read()

    def _load_learned_focus(self, focus_path: Optional[str]) -> Dict[str, Any]:
        """Load learned focus areas JSON"""
        if not focus_path:
            return {}

        full_path = self.base_path / focus_path
        if not full_path.exists():
            return {}

        with open(full_path, "r") as f:
            return json.load(f)

    def _build_system_prompt(
        self,
        prefix: str,
        prompt_template: str,
        learned_focus: Dict[str, Any],
        agent_name: str = None,
        mrs_context: Optional[str] = None
    ) -> str:
        """
        Construct complete system prompt including learned patterns.

        The system prompt combines:
        1. Agent identity and role (prefix)
        2. Task-specific instructions (prompt_template)
        3. Learned focus areas (dynamically updated)
        4. MRS context (beliefs, reflections, codex) - for agents with MRS access
        """
        parts = []

        if prefix.strip():
            parts.append(prefix.strip())

        parts.append(prompt_template.strip())

        # Add learned focus summary if available
        if learned_focus:
            focus_summary = self._format_learned_focus(learned_focus)
            if focus_summary:
                parts.append("\n# CURRENT LEARNED PATTERNS:")
                parts.append(focus_summary)

        # Add MRS context if provided (for agents with MRS integration enabled)
        if mrs_context:
            parts.append("\n# MRS CONTEXT (Your Memory & Reasoning):")
            parts.append(mrs_context)

        return "\n\n".join(parts)

    def _load_mrs_context(self, agent_name: str) -> str:
        """
        Load MRS context for agents with MRS integration.

        Loads:
        - Active beliefs from belief ledger
        - Pending reflections
        - Recent patterns detected
        - Key Codex facts

        This gives the agent self-awareness of their own learning/memory.
        """
        try:
            # Import MRS components
            import sys
            mrs_path = self.base_path / "mrs"
            if str(mrs_path) not in sys.path:
                sys.path.insert(0, str(mrs_path))

            from analysis.belief_manager import BeliefManager
            from analysis.reflection_engine import ReflectionEngine

            belief_manager = BeliefManager(
                ledger_path=str(mrs_path / "memory" / "belief_ledger.json"),
                reflections_path=str(mrs_path / "memory" / "reflections.json")
            )

            reflection_engine = ReflectionEngine(
                outcomes_path=str(mrs_path / "memory" / "outcomes.json"),
                sessions_path=str(self.base_path / "memory" / "sessions"),
                reflections_path=str(mrs_path / "memory" / "reflections.json")
            )

            context_parts = []

            # Active Beliefs Only - clean injection, no stats
            active_beliefs = belief_manager.get_active_beliefs(agent_name)
            if active_beliefs:
                context_parts.append("## Active Beliefs:")
                for belief in active_beliefs[:36]:  # Seed Lattice: 36 beliefs maximum
                    context_parts.append(f"- {belief.get('content')}")

            # If no beliefs, inject nothing (silence, not confabulation)
            if not context_parts:
                return ""

            return "\n".join(context_parts)

        except Exception as e:
            # MRS not available or error loading - gracefully degrade
            return f"MRS context unavailable: {str(e)}"

    def _format_learned_focus(self, learned_focus: Dict[str, Any]) -> str:
        """Format learned focus areas for prompt injection"""
        if not learned_focus:
            return ""

        lines = []
        for pattern_id, pattern_data in learned_focus.items():
            count = pattern_data.get("count", 0)
            last_seen = pattern_data.get("last_seen", "unknown")
            description = pattern_data.get("description", pattern_id)

            lines.append(
                f"- [{pattern_id}] {description} "
                f"(occurred {count} times; last: {last_seen})"
            )

        return "\n".join(lines)

    def get_agent_capabilities(self, agent_name: str, forge_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get agent capabilities and performance metrics.

        Returns:
            Dict with capabilities, focus areas, and learning stats
        """
        agent_data = self.load_agent(agent_name, forge_config)

        capabilities = agent_data["base_config"].get("tasks", {})
        learned_patterns = len(agent_data.get("learned_focus", {}))

        return {
            "agent": agent_name,
            "display_name": agent_data["display_name"],
            "role": agent_data["role"],
            "capabilities": list(capabilities.keys()),
            "learned_patterns": learned_patterns,
            "current_model": agent_data["model"],
        }
