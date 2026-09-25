"""
JARVIS V2 - FastAPI REST API Service
Exposes internal orchestration, tool execution, memory, tasks, and system health endpoints
with strict Bearer token authentication and user-scoped data isolation.
"""
import uuid
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from core.orchestrator import orchestrator
from tools.registry import tool_registry
from storage.supabase import storage_adapter
from observability.metrics import metrics_tracker
from models.health import provider_health
from security.authentication import auth_manager, UserSession

app = FastAPI(
    title="JARVIS V2 API Service",
    description="Autonomous Multimodal AI Agent OS - REST Interface",
    version="2.0.0"
)

class ChatRequest(BaseModel):
    prompt: str
    channel: str = "api"

class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class LoginRequest(BaseModel):
    email: str
    password: str

from storage.supabase import DEFAULT_SYSTEM_USER_UUID

def get_current_user(authorization: Optional[str] = Header(None)) -> UserSession:
    """Authenticates API requests via Bearer token with strict production enforcement."""
    if not authorization:
        if config.ENVIRONMENT == "development":
            # Explicit local development mode fallback using canonical dev UUID
            return UserSession(user_id=DEFAULT_SYSTEM_USER_UUID, role="owner", channel="api")
        raise HTTPException(status_code=401, detail="Authentication required: missing Authorization Bearer token.")

    session = auth_manager.authenticate_bearer_token(authorization)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired Bearer authentication token.")
    return session


@app.post("/api/auth/login")
def login(req: LoginRequest):
    """Authenticates with email and password returning access token."""
    result = storage_adapter.auth_sign_in(req.email, req.password)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed."))
    return result.get("data")

@app.get("/api/health")
def get_health():
    return {
        "status": "online",
        "storage": "supabase_connected" if storage_adapter.is_supabase_connected else "local_sqlite_active",
        "registered_tools_count": len(tool_registry.list_tools()),
        "provider_stats": provider_health.stats
    }

@app.get("/api/metrics")
def get_metrics():
    return metrics_tracker.get_summary()

@app.get("/api/tasks")
def list_tasks(current_user: UserSession = Depends(get_current_user)):
    tasks = storage_adapter.get_tasks(status="pending", user_id=current_user.user_id, auth_token=current_user.access_token)
    return [t.model_dump() for t in tasks]

@app.get("/api/memory")
def list_memories(limit: int = 20, current_user: UserSession = Depends(get_current_user)):
    return storage_adapter.get_all_memories(limit=limit, user_id=current_user.user_id, auth_token=current_user.access_token)

@app.post("/api/chat")
def chat(req: ChatRequest, current_user: UserSession = Depends(get_current_user)):
    start_time = time.time()
    tokens = []
    for token in orchestrator.execute_turn(
        req.prompt,
        history=[],
        user_id=current_user.user_id,
        channel=req.channel,
        session_id=current_user.session_id,
        auth_token=current_user.access_token
    ):
        tokens.append(token)
    reply = "".join(tokens)
    metrics_tracker.record_request(latency_ms=(time.time() - start_time) * 1000.0, success=True)
    return {"reply": reply, "user_id": current_user.user_id}

@app.post("/api/tool/execute")
def execute_tool(req: ToolExecutionRequest, current_user: UserSession = Depends(get_current_user)):
    try:
        res = tool_registry.execute_tool(
            req.tool_name,
            req.arguments,
            user_id=current_user.user_id,
            channel="api",
            session_id=current_user.session_id,
            auth_token=current_user.access_token
        )
        return {"success": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
