import os
import re
import json
import time
import uuid
import secrets
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth_db
from core_engine import fast_web_search, build_evidence_pack, generate_grounded_answer, verify_answer, diagnose_feedback_issue

# Initialize database tables on server start
auth_db.init_db()

app = FastAPI(
    title="Hallucination Detector",
    description="High-performance, web-grounded AI hallucination detection & fact-checking server.",
    version="3.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Sessions In-Memory Store (Mapped to DB Users)
# ---------------------------------------------------------------------------
ACTIVE_SESSIONS = {}  # token -> {"user_id": int, "username": str, "is_admin": bool, "expires": float}

def create_session(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    ACTIVE_SESSIONS[token] = {
        "user_id": user["id"],
        "username": user["username"],
        "is_admin": bool(user["is_admin"]),
        "created_at": datetime.now().timestamp()
    }
    return token

def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session_token")
    if not token or token not in ACTIVE_SESSIONS:
        return None
    return ACTIVE_SESSIONS[token]

def require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Administrator privileges required.")
    return user

# ---------------------------------------------------------------------------
# Global Visitor Tracking Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def track_visitors_middleware(request: Request, call_next):
    # Skip tracking for static files (css, js, images, favicon)
    path = request.url.path
    if not path.startswith("/static") and not path.endswith((".ico", ".png", ".jpg", ".svg", ".css", ".js")):
        client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        user_agent = request.headers.get("user-agent", "")
        referrer = request.headers.get("referer", "")
        token = request.cookies.get("session_token")
        user_id = ACTIVE_SESSIONS.get(token, {}).get("user_id") if token else None

        auth_db.log_visitor(
            ip=client_ip,
            user_agent=user_agent,
            path=path,
            referrer=referrer,
            user_id=user_id
        )

    response = await call_next(request)
    return response

# ---------------------------------------------------------------------------
# Pydantic Request Schemas
# ---------------------------------------------------------------------------
class RegisterPayload(BaseModel):
    username: str
    password: str

class LoginPayload(BaseModel):
    username: str
    password: str

class ChatPayload(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    history: Optional[List[dict]] = None

class FeedbackPayload(BaseModel):
    message_id: str
    query: str
    answer: str
    rating: str  # "thumbs_up" or "thumbs_down"
    comment: Optional[str] = ""

class SaveChatPayload(BaseModel):
    id: str
    title: str
    messages: list

class AdminBlockPayload(BaseModel):
    block: bool

class AdminResetPasswordPayload(BaseModel):
    new_password: str

class AdminResolveFeedbackPayload(BaseModel):
    approved: bool = True
    resolution_note: Optional[str] = ""

# ---------------------------------------------------------------------------
# HTML Frontend Route
# ---------------------------------------------------------------------------
@app.get("/", response_class=FileResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Hallucination Detector loading...</h2>")

@app.get("/admin", response_class=FileResponse)
async def serve_admin_panel():
    index_path = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_path)

# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/auth/register")
async def register(payload: RegisterPayload, response: Response, request: Request):
    ok, msg = auth_db.register_user(payload.username, payload.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    # Auto-login on registration
    ok_auth, auth_msg, user_dict = auth_db.authenticate_user(payload.username, payload.password)
    if ok_auth and user_dict:
        token = create_session(user_dict)
        response.set_cookie(key="session_token", value=token, httponly=True, samesite="lax", max_age=86400 * 30)
        return {"success": True, "message": msg, "user": user_dict}
    return {"success": True, "message": msg}

@app.post("/api/auth/login")
async def login(payload: LoginPayload, response: Response, request: Request):
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    user_agent = request.headers.get("user-agent", "")
    
    ok, msg, user_dict = auth_db.authenticate_user(payload.username, payload.password)
    status_str = "SUCCESS" if ok else ("BLOCKED" if "suspended" in msg else "FAILED")
    
    auth_db.log_login_event(
        username=payload.username,
        ip=client_ip,
        user_agent=user_agent,
        status=status_str,
        user_id=user_dict["id"] if user_dict else None
    )

    if not ok or not user_dict:
        raise HTTPException(status_code=401, detail=msg)

    token = create_session(user_dict)
    response.set_cookie(key="session_token", value=token, httponly=True, samesite="lax", max_age=86400 * 30)
    return {"success": True, "user": user_dict}

@app.post("/api/auth/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    response.delete_cookie("session_token")
    return {"success": True, "message": "Logged out."}

@app.get("/api/auth/me")
async def get_me(request: Request):
    user = get_current_user(request)
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}

@app.delete("/api/user/account")
async def delete_account(response: Response, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in.")
    if user.get("is_admin") and user.get("username").lower() == "admin":
        raise HTTPException(status_code=400, detail="The default administrator account cannot be deleted.")
    auth_db.delete_user_account(user["user_id"])
    token = request.cookies.get("session_token")
    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    response.delete_cookie("session_token")
    return {"success": True, "message": "Account and all associated data permanently deleted."}

# ---------------------------------------------------------------------------
# Chat & Conversations Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/conversations")
async def get_conversations(request: Request):
    user = get_current_user(request)
    if not user:
        return {"conversations": []}
    convs = auth_db.load_user_conversations(user["user_id"])
    return {"conversations": convs}

@app.post("/api/conversations")
async def save_conversation(payload: SaveChatPayload, request: Request):
    user = get_current_user(request)
    if not user:
        return {"success": False, "message": "Guest chat (not persisted to cloud)."}
    auth_db.save_user_conversation(user["user_id"], payload.model_dump())
    return {"success": True}

@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return {"success": True}
    auth_db.delete_user_conversation(user["user_id"], conv_id)
    return {"success": True}

# ---------------------------------------------------------------------------
# Core Fast Chat Endpoint
# ---------------------------------------------------------------------------
@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload, request: Request):
    q = payload.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question.")

    # 1. Parallel Web Search
    t_start = time.time()
    sources = fast_web_search(q)
    evidence_pack = build_evidence_pack(sources)

    # 2. Format recent conversation history
    history_str = ""
    if payload.history:
        lines = []
        for h in payload.history[-4:]:
            role = h.get("role", "user")
            content = h.get("content", "")[:250]
            lines.append(f"{role.capitalize()}: {content}")
        history_str = "\n".join(lines)

    # 3. Grounded Answer Generation
    gen_result = generate_grounded_answer(q, evidence_pack, history_context=history_str)
    answer = gen_result.get("answer", "")
    model_name = gen_result.get("model", "gemini-3.5-flash")

    # 4. Hallucination Verification
    verification = verify_answer(q, answer, sources)
    elapsed = round(time.time() - t_start, 2)
    message_id = str(uuid.uuid4())

    return {
        "message_id": message_id,
        "answer": answer,
        "model": model_name,
        "verification": verification,
        "sources": sources,
        "elapsed": elapsed
    }

# ---------------------------------------------------------------------------
# Thumbs Up / Down Feedback Endpoint (Claude/ChatGPT style)
# ---------------------------------------------------------------------------
@app.post("/api/feedback")
async def submit_feedback(payload: FeedbackPayload, request: Request):
    user = get_current_user(request)
    user_id = user["user_id"] if user else None
    username = user["username"] if user else "Anonymous"

    ok, msg = auth_db.record_feedback(
        message_id=payload.message_id,
        query=payload.query,
        answer=payload.answer,
        rating=payload.rating,
        user_id=user_id,
        username=username,
        comment=payload.comment or ""
    )
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": "Feedback saved. Thank you!"}

# ---------------------------------------------------------------------------
# Admin Analytics & Management Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/admin/analytics")
async def get_admin_data(request: Request):
    admin = require_admin(request)
    analytics = auth_db.get_admin_analytics(admin["user_id"])
    if not analytics:
        raise HTTPException(status_code=403, detail="Unauthorized.")
    return analytics

@app.get("/api/admin/users")
async def get_admin_users(request: Request):
    admin = require_admin(request)
    users = auth_db.get_all_users_for_admin(admin["user_id"])
    return {"users": users}

@app.post("/api/admin/users/{user_id}/toggle-block")
async def admin_toggle_block(user_id: int, payload: AdminBlockPayload, request: Request):
    admin = require_admin(request)
    ok, msg = auth_db.toggle_user_block(admin["user_id"], user_id, payload.block)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/admin/users/{user_id}/reset-password")
async def admin_reset_password(user_id: int, payload: AdminResetPasswordPayload, request: Request):
    admin = require_admin(request)
    ok, msg = auth_db.admin_reset_user_password(admin["user_id"], user_id, payload.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

# ---------------------------------------------------------------------------
# Admin Feedback Diagnostic & Permission Resolution Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/admin/feedback/{feedback_id}/diagnose")
async def admin_diagnose_feedback_endpoint(feedback_id: int, request: Request):
    admin = require_admin(request)
    fb = auth_db.get_feedback_by_id(feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback entry not found.")

    diag = diagnose_feedback_issue(
        question=fb.get("query") or "",
        original_answer=fb.get("answer") or "",
        user_comment=fb.get("comment") or ""
    )

    diag_json = json.dumps({
        "why_negative": diag["why_negative"],
        "root_cause": diag["root_cause"],
        "system_recommendation": diag["system_recommendation"]
    })
    auth_db.save_feedback_diagnosis(
        feedback_id=feedback_id,
        diagnosis=diag_json,
        proposed_fix=diag["proposed_answer"]
    )

    return {
        "success": True,
        "feedback_id": feedback_id,
        "diagnosis": diag
    }

@app.post("/api/admin/feedback/{feedback_id}/resolve")
async def admin_resolve_feedback_endpoint(feedback_id: int, payload: AdminResolveFeedbackPayload, request: Request):
    admin = require_admin(request)
    fb = auth_db.get_feedback_by_id(feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback entry not found.")

    ok, msg = auth_db.resolve_feedback_with_permission(
        feedback_id=feedback_id,
        admin_username=admin["username"],
        approved=payload.approved,
        resolution_note=payload.resolution_note or ""
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
