"""thin wrapper over litellm. mock mode returns canned responses, no api calls."""
from agent.config import MOCK_MODE

MOCK_REPLY = "Based on what I found, here's some general wellness guidance. (mock response)"


def _mock_completion(messages, tools):
    last = messages[-1]["content"] if messages else ""
    already_called_tool = any(m.get("role") == "tool" for m in messages)
    # fake exactly one tool call per user turn, then answer
    if tools and not already_called_tool:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_mock1",
                "function": {"name": tools[0]["function"]["name"], "arguments": '{"query": "' + last[:30] + '"}'},
            }],
        }
    return {"role": "assistant", "content": MOCK_REPLY, "tool_calls": None}


def chat(messages, tools, provider, model):
    if MOCK_MODE:
        return _mock_completion(messages, tools)

    import time
    import litellm

    last_err = None
    for attempt in range(8):
        try:
            resp = litellm.completion(model=f"{provider}/{model}", messages=messages, tools=tools)
            msg = resp.choices[0].message
            if provider == "openai":
                time.sleep(8)  # this account's tier mislabels rate-limit rejections as 401 - pace to avoid it
            return {"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls}
        except litellm.RateLimitError as e:
            last_err = e
            time.sleep(10 * (attempt + 1))
        except litellm.AuthenticationError as e:
            # this account's tier mislabels rate-limit rejections as 401 - retry with backoff, don't hard-fail
            last_err = e
            time.sleep(8 * (attempt + 1))
        except (litellm.InternalServerError, litellm.APIConnectionError) as e:
            # transient network/dns hiccups observed mid-batch-run - retry
            last_err = e
            time.sleep(5 * (attempt + 1))
        except litellm.BadRequestError as e:
            # llama/groq occasionally emits malformed tool-call syntax it can't parse itself -
            # not transient, retrying the same prompt won't help. surfaces as a per-turn eval finding.
            raise RuntimeError(f"llm_client.chat: model failed to produce a valid tool call: {e}")
    raise RuntimeError(f"llm_client.chat: failed after 8 retries. last error: {last_err}")
