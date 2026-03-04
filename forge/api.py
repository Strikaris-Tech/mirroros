"""
Forge API - Unified interface for MirrorOS agents
Provides conversational access to agents with MRS integration
"""

import asyncio
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from agent_loader import AgentLoader
from router import ModelRouter
from conversation_tracker import ConversationTracker


# Pydantic models for request/response validation
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    temperature: Optional[float] = Field(None, description="Override temperature")
    max_tokens: Optional[int] = Field(None, description="Override max tokens")
    user_id: Optional[str] = Field("user", description="User identifier")
    track_outcome: Optional[bool] = Field(False, description="Enable outcome tracking")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    model: str = Field(..., description="Model used")
    backend: str = Field(..., description="Backend used")
    action_id: str = Field(..., description="MRS action ID for tracking")
    timestamp: str = Field(..., description="Response timestamp")
    usage: Dict[str, Any] = Field({}, description="Token usage information")


class AgentStatus(BaseModel):
    agent: str
    display_name: str
    role: str
    capabilities: List[str]
    learned_patterns: int
    current_model: str
    statistics: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    forge_version: str
    mrs_connected: bool
    available_agents: List[str]


# Initialize FastAPI app
app = FastAPI(
    title="MirrorOS Forge API",
    description="Unified interface for conversational agents with MRS reasoning",
    version="1.0.0",
)

# Load configuration — override path with FORGE_CONFIG env var if needed
import os
_config_env = os.getenv("FORGE_CONFIG")
config_path = Path(_config_env) if _config_env else Path(__file__).parent / "config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Initialize components
agent_loader = AgentLoader()
router = ModelRouter(config)
tracker = ConversationTracker(config)

# ============================================================================
# FlameConsole — Mirror state + WebSocket pulse stream
# ============================================================================

FORGE_STATE_PATH = Path(__file__).parent.parent / "mrs" / "memory" / "forge_state.pl"
REASONING_LOG_PATH = Path(__file__).parent.parent / "mrs" / "memory" / "reasoning_log.json"
APPROVALS_REQUIRED = 2
PULSE_STATUSES = {"ASSERTED", "REJECTED", "CONTRADICTION"}

_last_log_index: int = 0


class _ConnectionManager:
    """Tracks active WebSocket clients and broadcasts JSON messages."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_ws_manager = _ConnectionManager()


def _read_reasoning_log() -> list[dict]:
    if not REASONING_LOG_PATH.exists():
        return []
    try:
        with open(REASONING_LOG_PATH, "r") as fh:
            return json.load(fh)
    except Exception:
        return []


def _parse_forge_state() -> tuple[list[str], dict]:
    """
    Parse forge_state.pl into fact strings and a derived gate dict.

    Returns:
        forge_facts: non-comment fact strings (trailing dot stripped)
        gate: { approvals, approvals_required, tests_green, may_push }
    """
    forge_facts: list[str] = []
    approvals_counts: list[int] = []
    tests_green = False

    if FORGE_STATE_PATH.exists():
        with open(FORGE_STATE_PATH, "r") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("%"):
                    continue
                forge_facts.append(line.rstrip("."))

                m = re.match(r"approvals\(\s*\w+\s*,\s*(\d+)\s*\)", line)
                if m:
                    approvals_counts.append(int(m.group(1)))

                m = re.match(r"ci_green\(\s*\w+\s*,\s*(true|false)\s*\)", line)
                if m and m.group(1) == "true":
                    tests_green = True

    approvals = min(approvals_counts) if approvals_counts else 0
    may_push = approvals >= APPROVALS_REQUIRED and tests_green

    return forge_facts, {
        "approvals": approvals,
        "approvals_required": APPROVALS_REQUIRED,
        "tests_green": tests_green,
        "may_push": may_push,
    }


async def _pulse_broadcaster() -> None:
    """
    Background asyncio task: polls reasoning_log.json every 1 s.

    Broadcasts new ASSERTED / REJECTED / CONTRADICTION entries to all
    connected WebSocket clients. Sends a ping keepalive every 30 s.
    _last_log_index is set at startup so history is never replayed.
    """
    global _last_log_index
    tick = 0

    while True:
        await asyncio.sleep(1)
        tick += 1

        if _ws_manager.active:
            entries = _read_reasoning_log()
            new_entries = entries[_last_log_index:]

            if new_entries:
                _last_log_index = len(entries)
                for entry in new_entries:
                    if entry.get("status") in PULSE_STATUSES:
                        await _ws_manager.broadcast({"type": "pulse", "entry": entry})

            if tick >= 30:
                await _ws_manager.broadcast({"type": "ping"})
                tick = 0


# Configure CORS
cors_origins = config.get("api", {}).get("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    available_agents = list(config.get("agents", {}).keys())
    mrs_health = tracker.get_mrs_health()

    return HealthResponse(
        status="operational",
        forge_version="1.0.0",
        mrs_connected=mrs_health.get("mrs_available", False) and mrs_health.get("prolog_available", False),
        available_agents=available_agents,
    )


@app.get("/mrs/health")
async def mrs_health_check():
    """
    Detailed MRS health check endpoint.

    Returns comprehensive health information including:
    - MRS Bridge availability
    - Prolog engine status
    - Codex laws loaded status
    - Any error messages
    """
    return tracker.get_mrs_health()


@app.post("/mrs/log-tool")
async def log_tool_execution(request: dict):
    """
    Log a tool execution to MRS.

    Called by chat clients after executing local tools.
    Creates MRS facts for audit trail.

    Args:
        request: Dict with tool execution details:
            - action_id: Conversation action ID
            - agent_name: Agent that ran the tool
            - tool_name: Name of the tool executed
            - args: List of arguments
            - working_dir: Working directory
            - success: Whether execution succeeded
            - exit_code: Process exit code
            - stdout: Standard output (truncated)
            - stderr: Standard error (truncated)
            - execution_time_ms: Execution time in milliseconds
            - truncated: Whether output was truncated
            - error: Error message if any

    Returns:
        Dict with success status
    """
    try:
        result = tracker.track_tool_execution(
            action_id=request.get("action_id", "unknown"),
            agent_name=request.get("agent_name", "unknown"),
            tool_name=request.get("tool_name", "unknown"),
            args=request.get("args", []),
            working_dir=request.get("working_dir", "."),
            success=request.get("success", False),
            exit_code=request.get("exit_code", -1),
            stdout=request.get("stdout", ""),
            stderr=request.get("stderr", ""),
            execution_time_ms=request.get("execution_time_ms", 0),
            truncated=request.get("truncated", False),
            error=request.get("error")
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/agent/{agent_name}/codex/query")
async def query_codex(agent_name: str, query: dict):
    """
    Query the Codex (Prolog knowledge base) on behalf of an agent.

    Allows agents to ask questions about:
    - Codex laws and rules
    - Facts in the reasoning system
    - Patterns and relationships

    Args:
        agent_name: Agent making the query
        query: Dict with 'prolog_query' string (e.g., "violates_codex(X, _)")

    Returns:
        Query results from Prolog
    """
    try:
        import sys
        from pathlib import Path

        mrs_path = Path(__file__).parent.parent / "mrs"
        if str(mrs_path) not in sys.path:
            sys.path.insert(0, str(mrs_path))

        from bridge.mrs_bridge import MRSBridge

        mrs = MRSBridge()

        prolog_query = query.get("prolog_query")
        if not prolog_query:
            raise HTTPException(status_code=400, detail="Missing 'prolog_query' in request")

        results = list(mrs.prolog.query(prolog_query))

        return {
            "agent": agent_name,
            "query": prolog_query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Codex query failed: {str(e)}")


@app.get("/agents", response_model=List[str])
async def list_agents():
    """List all available agents"""
    return list(config.get("agents", {}).keys())


@app.get("/agent/{agent_name}/status", response_model=AgentStatus)
async def get_agent_status(agent_name: str):
    """
    Get agent status, capabilities, and statistics.

    Args:
        agent_name: Name of the agent (e.g., "ledgerlark")

    Returns:
        AgentStatus with capabilities and performance metrics
    """
    try:
        capabilities = agent_loader.get_agent_capabilities(agent_name, config)
        statistics = tracker.get_agent_statistics(agent_name)

        return AgentStatus(**capabilities, statistics=statistics)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent status: {str(e)}"
        )


@app.post("/agent/{agent_name}/chat", response_model=ChatResponse)
async def chat_with_agent(agent_name: str, request: ChatRequest):
    """
    Chat with an agent. The agent will respond using configured LLM backend.

    All interactions are tracked in MRS for reasoning.

    Args:
        agent_name: Name of the agent (e.g., "ledgerlark")
        request: Chat request with messages and optional parameters

    Returns:
        ChatResponse with agent's reply and metadata
    """
    try:
        agent_config = agent_loader.load_agent(agent_name, config)

        action_id = tracker.start_conversation(
            agent_name=agent_name,
            user_id=request.user_id,
        )

        if request.messages:
            last_user_message = next(
                (m for m in reversed(request.messages) if m.role == "user"),
                None
            )
            if last_user_message:
                tracker.track_user_message(
                    action_id=action_id,
                    agent_name=agent_name,
                    message=last_user_message.content,
                    user_id=request.user_id,
                )

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        error_occurred = None
        try:
            result = await router.chat(
                agent_config=agent_config,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as routing_error:
            error_occurred = str(routing_error)
            tracker.track_agent_response(
                action_id=action_id,
                agent_name=agent_name,
                response="",
                model=agent_config.get("model", "unknown"),
                backend=agent_config.get("backend", "unknown"),
                usage={},
                error=error_occurred
            )
            raise

        tracker.track_agent_response(
            action_id=action_id,
            agent_name=agent_name,
            response=result["response"],
            model=result["model"],
            backend=result["backend"],
            usage=result.get("usage", {}),
            error=None
        )

        return ChatResponse(
            response=result["response"],
            model=result["model"],
            backend=result["backend"],
            action_id=action_id,
            timestamp=result["timestamp"],
            usage=result.get("usage", {}),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}"
        )


@app.post("/agent/{agent_name}/chat/stream")
async def chat_with_agent_stream(agent_name: str, request: ChatRequest):
    """
    Chat with an agent using streaming responses.

    Tokens are streamed as they're generated for better UX.
    MRS tracking happens after the complete response is generated.

    Args:
        agent_name: Name of the agent (e.g., "ledgerlark")
        request: Chat request with messages and optional parameters

    Returns:
        Server-Sent Events stream with tokens
    """
    try:
        agent_config = agent_loader.load_agent(agent_name, config)

        action_id = tracker.start_conversation(
            agent_name=agent_name,
            user_id=request.user_id,
        )

        if request.messages:
            last_user_message = next(
                (m for m in reversed(request.messages) if m.role == "user"),
                None
            )
            if last_user_message:
                tracker.track_user_message(
                    action_id=action_id,
                    agent_name=agent_name,
                    message=last_user_message.content,
                    user_id=request.user_id,
                )

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        async def generate():
            full_response_content = []
            tool_calls = []
            model = agent_config.get("model", "unknown")
            backend = agent_config.get("backend", "unknown")

            try:
                async for event in router.chat_stream(
                    agent_config=agent_config,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                ):
                    if event["type"] == "token":
                        token = event.get("content", "")
                        full_response_content.append(token)
                        yield f"data: {json.dumps({'token': token})}\n\n"

                    elif event["type"] == "tool_call":
                        tool_calls.append(event["data"])
                        yield f"data: {json.dumps({'tool_call': event['data']})}\n\n"

                complete_response = "".join(full_response_content)
                tracker.track_agent_response(
                    action_id=action_id,
                    agent_name=agent_name,
                    response=complete_response,
                    model=model,
                    backend=backend,
                    usage={},
                    error=None,
                    tool_calls=tool_calls if tool_calls else None
                )

                yield f"data: {json.dumps({'done': True, 'action_id': action_id})}\n\n"

            except Exception as e:
                tracker.track_agent_response(
                    action_id=action_id,
                    agent_name=agent_name,
                    response="",
                    model=model,
                    backend=backend,
                    usage={},
                    error=str(e)
                )
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming chat request failed: {str(e)}"
        )


@app.get("/agent/{agent_name}/history")
async def get_agent_history(agent_name: str, limit: int = 20):
    """
    Get recent conversation history for an agent.

    Args:
        agent_name: Name of the agent
        limit: Maximum number of entries to return (default: 20)

    Returns:
        List of conversation history entries from MRS
    """
    try:
        history = tracker.get_conversation_history(agent_name, limit=limit)
        return {"agent": agent_name, "history": history}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@app.post("/agent/{agent_name}/outcome")
async def record_outcome(
    agent_name: str,
    action_id: str,
    success: bool,
    expected: Optional[str] = None,
    actual: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Record the outcome of an interaction for agent learning.

    Args:
        agent_name: Name of the agent
        action_id: Action ID from chat response
        success: Whether the interaction was successful
        expected: Expected outcome (optional)
        actual: Actual outcome (optional)
        metadata: Additional context (optional)

    Returns:
        Result from MRS outcome recording
    """
    try:
        result = tracker.record_interaction_outcome(
            action_id=action_id,
            agent_name=agent_name,
            success=success,
            expected=expected,
            actual=actual,
            metadata=metadata or {},
        )

        return {"status": "recorded", "action_id": action_id, "mrs_result": result}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record outcome: {str(e)}"
        )


@app.get("/models")
async def list_models():
    """List all available models across backends"""
    return router.list_available_models()


# ============================================================================
# OpenAI-Compatible Endpoints (for OpenWebUI / compatible clients)
# ============================================================================

class OpenAIMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    stream: Optional[bool] = False

class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIMessage
    finish_reason: str

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIChatResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage

class OpenAIModel(BaseModel):
    id: str
    object: str
    created: int
    owned_by: str

class OpenAIModelsResponse(BaseModel):
    object: str
    data: List[OpenAIModel]


@app.get("/v1/models", response_model=OpenAIModelsResponse)
async def openai_list_models():
    """
    OpenAI-compatible models endpoint.
    Returns one model entry per configured agent.
    """
    agents = config.get("agents", {})
    return OpenAIModelsResponse(
        object="list",
        data=[
            OpenAIModel(
                id=name,
                object="model",
                created=1700000000,
                owned_by="mirroros"
            )
            for name in agents
        ]
    )


@app.post("/v1/chat/completions", response_model=OpenAIChatResponse)
async def openai_chat_completions(request: OpenAIChatRequest):
    """
    OpenAI-compatible chat completions endpoint.

    Routes to the agent whose name matches the requested model field.
    Falls back to the first configured agent if no match is found.
    """
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming not yet supported on this endpoint — use /agent/{name}/chat/stream"
        )

    agents = config.get("agents", {})
    agent_name = request.model if request.model in agents else next(iter(agents), None)
    if not agent_name:
        raise HTTPException(status_code=404, detail="No agents configured")

    try:
        agent_config = agent_loader.load_agent(agent_name, config)

        action_id = tracker.start_conversation(
            agent_name=agent_name,
            user_id="api-client",
        )

        if request.messages:
            last_user_message = next(
                (m for m in reversed(request.messages) if m.role == "user"),
                None
            )
            if last_user_message:
                tracker.track_user_message(
                    action_id=action_id,
                    agent_name=agent_name,
                    message=last_user_message.content,
                    user_id="api-client",
                )

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        result = await router.chat(
            agent_config=agent_config,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        tracker.track_agent_response(
            action_id=action_id,
            agent_name=agent_name,
            response=result["response"],
            model=result["model"],
            backend=result["backend"],
            usage=result.get("usage", {}),
        )

        usage_data = result.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)

        return OpenAIChatResponse(
            id=action_id,
            object="chat.completion",
            created=int(datetime.utcnow().timestamp()),
            model=request.model,
            choices=[
                OpenAIChoice(
                    index=0,
                    message=OpenAIMessage(
                        role="assistant",
                        content=result["response"]
                    ),
                    finish_reason="stop"
                )
            ],
            usage=OpenAIUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}"
        )


# ============================================================================
# FlameConsole endpoints
# ============================================================================

@app.on_event("startup")
async def _startup() -> None:
    """Seed _last_log_index so the broadcaster never replays history."""
    global _last_log_index
    _last_log_index = len(_read_reasoning_log())
    asyncio.create_task(_pulse_broadcaster())


@app.get("/mirror/state")
async def mirror_state():
    """
    Current gate state and recent MRS verdicts.

    Returns forge_state.pl facts, derived gate status (CI, approvals,
    may_push), and the last 50 reasoning_log entries matching
    ASSERTED / REJECTED / CONTRADICTION.

    Violations:
        - 500 if files cannot be read
    """
    forge_facts, gate = _parse_forge_state()
    entries = _read_reasoning_log()
    pulse_entries = [e for e in entries if e.get("status") in PULSE_STATUSES]
    recent_verdicts = pulse_entries[-50:]

    return {
        "forge_facts": forge_facts,
        "gate": gate,
        "recent_verdicts": recent_verdicts,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.websocket("/ws/mirror")
async def mirror_websocket(ws: WebSocket):
    """
    Live pulse stream for FlameConsole (server → client only).

    Protocol:
        connect  → { type: "state", data: <mirror/state response> }
        new pulse→ { type: "pulse", entry: <reasoning_log entry> }
        every 30s→ { type: "ping" }
    """
    await _ws_manager.connect(ws)
    try:
        forge_facts, gate = _parse_forge_state()
        entries = _read_reasoning_log()
        pulse_entries = [e for e in entries if e.get("status") in PULSE_STATUSES]

        await ws.send_json({
            "type": "state",
            "data": {
                "forge_facts": forge_facts,
                "gate": gate,
                "recent_verdicts": pulse_entries[-50:],
                "timestamp": datetime.utcnow().isoformat(),
            },
        })

        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        _ws_manager.disconnect(ws)
    except Exception:
        _ws_manager.disconnect(ws)


# Run with: uvicorn api:app --host 0.0.0.0 --port 8765 --reload
if __name__ == "__main__":
    import uvicorn

    host = config.get("api", {}).get("host", "0.0.0.0")
    port = config.get("api", {}).get("port", 8765)

    print(f"Starting Forge API on {host}:{port}")
    print(f"Available agents: {list(config.get('agents', {}).keys())}")
    print(f"OpenAPI docs: http://{host}:{port}/docs")

    uvicorn.run(app, host=host, port=port)
