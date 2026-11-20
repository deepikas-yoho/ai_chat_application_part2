import asyncio
import os
import time
import uuid
from collections import defaultdict, deque
from typing import AsyncIterator

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="AI Chat Application")

# Configure allowed frontend origins in .env for deployment.
origins = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo storage. Replace with a database for multi-worker/production deployment.
sessions: dict[str, dict] = {}
requests_by_token = defaultdict(deque)
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "20"))
RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
DEMO_TOKEN = os.getenv("APP_API_KEY", "local-demo-key")


class SessionCreate(BaseModel):
    title: str = "New chat"


class ChatRequest(BaseModel):
    message: str


def authenticate(token: str | None):
    if not token or token != DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def enforce_rate_limit(token: str):
    now = time.time()
    queue = requests_by_token[token]
    while queue and now - queue[0] > RATE_WINDOW_SECONDS:
        queue.popleft()
    if len(queue) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    queue.append(now)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions(x_api_key: str | None = Header(default=None)):
    authenticate(x_api_key)
    return [{"id": sid, "title": data["title"]} for sid, data in sessions.items()]


@app.post("/api/sessions")
def create_session(payload: SessionCreate, x_api_key: str | None = Header(default=None)):
    authenticate(x_api_key)
    sid = str(uuid.uuid4())
    sessions[sid] = {"title": payload.title[:80], "messages": []}
    return {"id": sid, "title": sessions[sid]["title"]}


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str, x_api_key: str | None = Header(default=None)):
    authenticate(x_api_key)
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]["messages"]


async def demo_reply(message: str) -> AsyncIterator[str]:
    answer = f"Demo response: I received your message: {message}. Connect an LLM provider in app/main.py to generate real AI answers."
    for word in answer.split(" "):
        yield word + " "
        await asyncio.sleep(0.045)


@app.post("/api/sessions/{session_id}/stream")
async def stream_message(
    session_id: str,
    payload: ChatRequest,
    x_api_key: str | None = Header(default=None),
):
    authenticate(x_api_key)
    enforce_rate_limit(x_api_key)
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    sessions[session_id]["messages"].append({"role": "user", "content": message})

    async def event_stream():
        answer_parts = []
        try:
            async for chunk in demo_reply(message):
                answer_parts.append(chunk)
                # Server-Sent Events format
                yield f"data: {chunk.replace(chr(10), ' ')}\n\n"
            answer = "".join(answer_parts).strip()
            sessions[session_id]["messages"].append({"role": "assistant", "content": answer})
            yield "event: done\ndata: [DONE]\n\n"
        except asyncio.CancelledError:
            raise

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/usage")
def usage(x_api_key: str | None = Header(default=None)):
    authenticate(x_api_key)
    return {
        "sessions": len(sessions),
        "messages": sum(len(s["messages"]) for s in sessions.values()),
        "rate_limit": RATE_LIMIT,
        "rate_window_seconds": RATE_WINDOW_SECONDS,
    }
