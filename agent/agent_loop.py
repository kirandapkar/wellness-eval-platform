import json
from agent import llm_client, memory
from agent.config import SYSTEM_PROMPT, VARIANTS
from agent.tools.lookup_kb import lookup_kb, TOOL_SCHEMA as KB_SCHEMA
from agent.tools.search_web import search_web, TOOL_SCHEMA as WEB_SCHEMA

TOOLS = [KB_SCHEMA, WEB_SCHEMA]
TOOL_FNS = {"lookup_kb": lookup_kb, "search_web": search_web}

MAX_TOOL_HOPS = 3


def run_turn(session_id: str, user_msg: str, variant: str = "frontier"):
    cfg = VARIANTS[variant]
    history = memory.get_history(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_msg}]

    memory.append(session_id, {"role": "user", "content": user_msg})

    tool_calls_made = []
    for _ in range(MAX_TOOL_HOPS):
        reply = llm_client.chat(messages, TOOLS, cfg["provider"], cfg["model"])
        if not reply.get("tool_calls"):
            memory.append(session_id, {"role": "assistant", "content": reply["content"]})
            return {"reply": reply["content"], "tool_calls": tool_calls_made}

        messages.append(reply)
        for tc in reply["tool_calls"]:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
                result = TOOL_FNS[name](**args)
            except (TypeError, json.JSONDecodeError, KeyError) as e:
                # oss model occasionally emits args that don't match the tool schema -
                # feed the error back so the model can self-correct, rather than crash the turn
                result = {"error": f"invalid arguments for {name}: {e}"}
            tool_calls_made.append({"tool": name, "args": tc["function"]["arguments"], "result": result})
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result)})

    return {"reply": "sorry, ran out of tool budget.", "tool_calls": tool_calls_made}
