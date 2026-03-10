"""
Conversation Tracker - Integrate Forge conversations with MRS
Every interaction creates MRS facts for reasoning and learning
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Configure debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add MRS bridge to path
sys.path.append(str(Path(__file__).parent.parent / "mrs"))

from bridge.mrs_bridge import MRSBridge


class ConversationTracker:
    """Track agent conversations and integrate with MRS reasoning system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.track_interactions = config.get("mrs", {}).get("track_all_interactions", True)
        self.track_outcomes = config.get("mrs", {}).get("log_outcomes", True)

        logger.info(f"ConversationTracker initializing...")
        logger.info(f"  track_interactions: {self.track_interactions}")
        logger.info(f"  track_outcomes: {self.track_outcomes}")
        
        # Initialize MRS Bridge with error handling
        try:
            logger.info("Initializing MRS Bridge...")
            self.mrs = MRSBridge()
            self.mrs_available = True
            logger.info("✓ MRS Bridge initialized successfully")
        except Exception as e:
            logger.error(f"MRS Bridge initialization failed: {e}", exc_info=True)
            print(f"Warning: MRS Bridge initialization failed: {e}")
            print("Continuing without MRS integration...")
            self.mrs = None
            self.mrs_available = False
        
        self.reflection_engine = None
        self.learning_available = False

    def start_conversation(
        self,
        agent_name: str,
        user_id: str = "user",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new conversation session."""
        logger.debug(f"start_conversation called: agent={agent_name}, user={user_id}")
        logger.debug(f"  track_interactions={self.track_interactions}, mrs_available={self.mrs_available}")
        
        if not self.track_interactions or not self.mrs_available:
            action_id = f"conv_{datetime.utcnow().timestamp()}"
            logger.debug(f"  Skipping MRS tracking, returning: {action_id}")
            return action_id

        try:
            fact = f"conversation_started({self._prolog_atom(user_id)}, {self._prolog_atom(agent_name)})"
            logger.debug(f"  Asserting fact: {fact}")
            result = self.mrs.assert_fact(fact, agent=agent_name)
            logger.debug(f"  MRS result: {result}")
            action_id = result.get("action_id", f"conv_{datetime.utcnow().timestamp()}")
            logger.info(f"✓ Conversation started: {action_id}")
        except Exception as e:
            logger.error(f"MRS tracking failed: {e}", exc_info=True)
            print(f"Warning: MRS tracking failed: {e}")
            action_id = f"conv_{datetime.utcnow().timestamp()}"

        return action_id

    def track_user_message(
        self,
        action_id: str,
        agent_name: str,
        message: str,
        user_id: str = "user"
    ) -> Dict[str, Any]:
        """Track a user message in MRS."""
        logger.debug(f"track_user_message called: action_id={action_id}, agent={agent_name}")
        logger.debug(f"  message length: {len(message)}")
        
        if not self.track_interactions or not self.mrs_available:
            logger.debug("  Skipping MRS tracking")
            return {"success": True, "action_id": action_id}

        try:
            sanitized = self._sanitize_for_prolog(message, max_length=200)
            fact = f'user_message("{action_id}", {self._prolog_atom(user_id)}, "{sanitized}")'
            logger.debug(f"  Asserting fact: {fact}")
            result = self.mrs.assert_fact(fact, agent=agent_name)
            logger.debug(f"  MRS result: {result}")
            logger.info(f"✓ User message tracked: {action_id}")
            return result
        except Exception as e:
            logger.error(f"MRS tracking failed: {e}", exc_info=True)
            print(f"Warning: MRS tracking failed: {e}")
            return {"success": False, "action_id": action_id, "error": str(e)}

    def track_agent_response(
        self,
        action_id: str,
        agent_name: str,
        response: str,
        model: str,
        backend: str,
        usage: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Track an agent's response in MRS."""
        logger.debug(f"track_agent_response called: action_id={action_id}, agent={agent_name}")
        logger.debug(f"  response length: {len(response)}, model: {model}, backend: {backend}")
        logger.debug(f"  error: {error}, tool_calls: {tool_calls}")
        
        if not self.track_interactions or not self.mrs_available:
            logger.debug("  Skipping MRS tracking")
            return {"success": True, "action_id": action_id}

        try:
            # Log the natural language response
            sanitized_response = self._sanitize_for_prolog(response, max_length=200)
            sanitized_model = self._sanitize_for_prolog(model, max_length=50)
            sanitized_backend = self._sanitize_for_prolog(backend, max_length=20)
            fact = f'agent_response("{action_id}", {self._prolog_atom(agent_name)}, "{sanitized_response}", "{sanitized_model}", "{sanitized_backend}")'
            logger.debug(f"  Asserting fact: {fact}")
            result = self.mrs.assert_fact(fact, agent=agent_name)
            logger.debug(f"  MRS result: {result}")

            # Log any tool calls
            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name", "unknown_tool")
                    tool_args = tool_call.get("function", {}).get("arguments", {})
                    sanitized_args = self._sanitize_for_prolog(json.dumps(tool_args), max_length=200)
                    tool_fact = f'agent_tool_call("{action_id}", "{tool_name}", "{sanitized_args}")'
                    logger.debug(f"  Asserting tool call fact: {tool_fact}")
                    self.mrs.assert_fact(tool_fact, agent=agent_name)

            if usage:
                self._log_usage(action_id, agent_name, usage)

            # Auto-log outcome
            if error:
                logger.info(f"Error detected, logging failure outcome: {action_id}")
                self._auto_log_outcome(
                    action_id=action_id,
                    agent_name=agent_name,
                    success=False,
                    actual=f"Error: {error}",
                    metadata={"error_type": "response_error", "model": model, "backend": backend}
                )
            elif not tool_calls: # Only log success if it's a final response, not a tool call
                logger.debug(f"Final response detected, logging positive outcome: {action_id}")
                self._auto_log_outcome(
                    action_id=action_id,
                    agent_name=agent_name,
                    success=True,
                    actual=f"Response generated ({len(response)} chars)",
                    metadata={"model": model, "backend": backend, "response_length": len(response)}
                )

            logger.info(f"✓ Agent response tracked: {action_id}")
            return result
        except Exception as e:
            logger.error(f"MRS tracking failed: {e}", exc_info=True)
            print(f"Warning: MRS tracking failed: {e}")
            
            # Log the tracking failure as an outcome
            self._auto_log_outcome(
                action_id=action_id,
                agent_name=agent_name,
                success=False,
                actual=f"Tracking error: {str(e)}",
                metadata={"error_type": "tracking_failure"}
            )
            
            return {"success": False, "action_id": action_id, "error": str(e)}

    def record_interaction_outcome(
        self,
        action_id: str,
        agent_name: str,
        success: bool,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record the outcome of an interaction for learning."""
        if not self.track_outcomes or not self.mrs_available:
            return {"success": True}

        try:
            result = self.mrs.record_outcome(
                action_id=action_id,
                expected=expected or "unknown",
                actual=actual or "unknown",
                success=success,
                metadata=metadata or {}
            )
            
            return result
        except Exception as e:
            logger.error(f"MRS outcome recording failed: {e}", exc_info=True)
            print(f"Warning: MRS outcome recording failed: {e}")
            return {"success": False, "error": str(e)}

    def track_tool_execution(
        self,
        action_id: str,
        agent_name: str,
        tool_name: str,
        args: List[str],
        working_dir: str,
        success: bool,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        execution_time_ms: float = 0,
        truncated: bool = False,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a tool execution in MRS.

        Creates facts:
        - tool_invocation(ActionId, ToolName, Args, WorkingDir)
        - tool_output(ActionId, ExitCode, ExecutionTimeMs, Truncated)
        - tool_validation_failure(ActionId, Reason) if error
        """
        logger.debug(f"track_tool_execution: {tool_name} args={args} success={success}")

        if not self.track_interactions or not self.mrs_available:
            logger.debug("  Skipping MRS tracking")
            return {"success": True, "action_id": action_id}

        try:
            # Log the invocation
            sanitized_args = self._sanitize_for_prolog(json.dumps(args), max_length=200)
            sanitized_dir = self._sanitize_for_prolog(working_dir, max_length=100)
            invocation_fact = f'tool_invocation("{action_id}", "{tool_name}", "{sanitized_args}", "{sanitized_dir}")'
            logger.debug(f"  Asserting: {invocation_fact}")
            self.mrs.assert_fact(invocation_fact, agent=agent_name)

            # Log the output/result
            output_fact = f'tool_output("{action_id}", {exit_code}, {int(execution_time_ms)}, {str(truncated).lower()})'
            logger.debug(f"  Asserting: {output_fact}")
            self.mrs.assert_fact(output_fact, agent=agent_name)

            # Log validation failure if there was an error
            if error:
                sanitized_error = self._sanitize_for_prolog(error, max_length=200)
                failure_fact = f'tool_validation_failure("{action_id}", "{sanitized_error}")'
                logger.debug(f"  Asserting: {failure_fact}")
                self.mrs.assert_fact(failure_fact, agent=agent_name)

            # Auto-log outcome
            self._auto_log_outcome(
                action_id=action_id,
                agent_name=agent_name,
                success=success,
                actual=f"Tool {tool_name}: exit_code={exit_code}",
                metadata={
                    "tool_name": tool_name,
                    "exit_code": exit_code,
                    "execution_time_ms": execution_time_ms,
                    "truncated": truncated
                }
            )

            logger.info(f"✓ Tool execution tracked: {tool_name} -> {exit_code}")
            return {"success": True, "action_id": action_id}

        except Exception as e:
            logger.error(f"Tool tracking failed: {e}", exc_info=True)
            return {"success": False, "action_id": action_id, "error": str(e)}

    def get_conversation_history(
        self,
        agent_name: str,
        limit: int = 20
    ) -> list:
        """Retrieve recent conversation history for an agent."""
        if not self.mrs_available:
            return []
        
        try:
            history = self.mrs.get_reasoning_history(agent=agent_name, limit=limit)
            return history
        except Exception as e:
            print(f"Warning: Failed to retrieve history: {e}")
            return []

    def get_mrs_health(self) -> Dict[str, Any]:
        """
        Get MRS system health status.

        Returns:
            Dict with MRS health information including Prolog status,
            Codex status, and learning engine availability.
        """
        health = {
            "mrs_available": self.mrs_available,
            "track_interactions": self.track_interactions,
            "track_outcomes": self.track_outcomes
        }

        if self.mrs_available and self.mrs:
            mrs_health = self.mrs.health_check()
            health.update(mrs_health)
        else:
            health["prolog_available"] = False
            health["codex_loaded"] = False
            health["error"] = "MRS Bridge not initialized"

        return health

    def get_agent_statistics(self, agent_name: str) -> Dict[str, Any]:
        """Get conversation statistics for an agent."""
        if not self.mrs_available:
            return {
                "agent": agent_name,
                "total_conversations": 0,
                "total_outcomes": 0,
                "successful_outcomes": 0,
                "success_rate": 0.0,
            }
        
        try:
            conversation_query = f'conversation_started(_, {agent_name})'
            conversations = self.mrs.query(conversation_query)

            history = self.mrs.get_reasoning_history(agent=agent_name, limit=100)
            outcomes = [
                entry for entry in history
                if entry.get("action") == "record_outcome"
            ]

            total_conversations = len(conversations)
            total_outcomes = len(outcomes)
            successful_outcomes = sum(
                1 for o in outcomes
                if o.get("details", {}).get("success", False)
            )

            success_rate = (
                (successful_outcomes / total_outcomes * 100)
                if total_outcomes > 0
                else 0.0
            )

            return {
                "agent": agent_name,
                "total_conversations": total_conversations,
                "total_outcomes": total_outcomes,
                "successful_outcomes": successful_outcomes,
                "success_rate": round(success_rate, 2),
            }
        except Exception as e:
            print(f"Warning: Failed to get statistics: {e}")
            return {
                "agent": agent_name,
                "total_conversations": 0,
                "total_outcomes": 0,
                "successful_outcomes": 0,
                "success_rate": 0.0,
            }

    def _sanitize_for_prolog(self, text: str, max_length: int = 200) -> str:
        """Sanitize text for safe Prolog fact insertion."""
        sanitized = text.replace('"', '\\"').replace("'", "\\'")
        sanitized = " ".join(sanitized.split())
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        return sanitized

    def _prolog_atom(self, text: str) -> str:
        """Convert a string to a valid Prolog atom by quoting and escaping."""
        # Escape single quotes and backslashes for Prolog atom syntax
        escaped = text.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    def _auto_log_outcome(
        self,
        action_id: str,
        agent_name: str,
        success: bool,
        actual: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Automatically log an outcome if outcome logging is enabled.
        This is called internally when we detect success/failure conditions.
        """
        if not self.track_outcomes or not self.mrs_available:
            logger.debug(f"  Auto-outcome skipped (track_outcomes={self.track_outcomes}, mrs_available={self.mrs_available})")
            return
        
        try:
            logger.debug(f"  Auto-logging outcome: success={success}")
            result = self.record_interaction_outcome(
                action_id=action_id,
                agent_name=agent_name,
                success=success,
                actual=actual,
                metadata=metadata or {}
            )
            logger.debug(f"  Outcome logged: {result.get('success')}")
        except Exception as e:
            logger.error(f"Failed to auto-log outcome: {e}", exc_info=True)

    def _log_usage(
        self,
        action_id: str,
        agent_name: str,
        usage: Dict[str, Any]
    ) -> None:
        """Log token usage metadata (optional)"""
        pass
