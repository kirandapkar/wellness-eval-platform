"""session store: session_id -> list of turns. in-memory dict, good enough for demo."""
from agent.config import MEMORY_MAX_TURNS

_sessions = {}


def get_history(session_id: str):
    return _sessions.get(session_id, [])


def append(session_id: str, msg: dict):
    _sessions.setdefault(session_id, []).append(msg)
    # truncate oldest first, keep last N turns
    if len(_sessions[session_id]) > MEMORY_MAX_TURNS * 2:
        _sessions[session_id] = _sessions[session_id][-MEMORY_MAX_TURNS * 2:]


def reset(session_id: str):
    _sessions.pop(session_id, None)
