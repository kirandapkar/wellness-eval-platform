from fastapi import FastAPI
from pydantic import BaseModel
from agent.agent_loop import run_turn
from agent import memory

app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    variant: str = "frontier"  # or "oss"


@app.post("/chat")
def chat(req: ChatRequest):
    return run_turn(req.session_id, req.message, req.variant)


@app.post("/reset")
def reset(session_id: str):
    memory.reset(session_id)
    return {"ok": True}
