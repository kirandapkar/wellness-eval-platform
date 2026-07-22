# Wellness Assistant + Evals Platform

Ollive take-home: one wellness agent spec, two model backends (OSS + frontier), an evals platform comparing them on hallucination, bias/harm, and content safety.

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # fill in keys
python -m agent.kb.build_index   # one-time: build the real Chroma KB index
```

Env vars needed (see `.env`):
- `OPENAI_API_KEY` — frontier agent (`gpt-4o-mini`) and judge (`gpt-4o`)
- `GROQ_API_KEY` — OSS agent (`llama-3.1-8b-instant` — see model-availability note below)
- `TAVILY_API_KEY` — `search_web` tool
- `MOCK_MODE` — `true` (default) runs everything on canned responses, no API calls. Set `false` to hit real APIs.

Run agent API:
```
uvicorn agent.main:app --reload
```

Run chat UI:
```
streamlit run ui/streamlit_app.py
```

Run evals (real mode):
```
python -m evals.calibrate_judge      # sanity-check judge against gold set first
python -m evals.run_evals --agent both      # supports --limit N for a quick subset, resumes on rerun
python -m evals.report                # writes EVAL_REPORT.md
python -m evals.cost_latency          # bonus: latency/cost bench
```

## Architecture

Single agent implementation (`agent/agent_loop.py`), model swapped via `VARIANTS` config in `agent/config.py` — not two separate codebases. This guarantees the "keep architecture fixed" requirement by construction: any prompt/tool/memory change applies identically to both variants.

- `agent/llm_client.py` — thin litellm wrapper, one function swaps provider/model
- `agent/tools/` — `lookup_kb` (Chroma + local sentence-transformer embeddings over the 9 KB docs, no embedding API cost), `search_web` (Tavily)
- `agent/memory.py` — in-memory session store, last N turns
- `evals/` — dataset (77 prompts, 8 categories), judge (OpenAI structured-output rubric), gold-set calibration, runner, report

Evals platform treats the agent as a function-level black box (`run_turn`), decoupled from the agent implementation itself so eval logic never needs to know about prompts/tools internally.

**Mock-first build:** every external call (LLM completion, KB embeddings, Tavily, judge) has a mock path used to build and test the entire pipeline end-to-end before spending a cent on real APIs. Real keys were swapped in and verified one integration at a time.

## Real eval results (77 prompts × 2 agents, 166/166 turns scored, 0 errors)

| Axis | OSS (Llama-3.1-8b, Groq) | Frontier (GPT-4o-mini) |
|---|---|---|
| Hallucination | 4.42 / 5 | 4.65 / 5 |
| Bias & Harmful | 4.67 / 5 | 4.83 / 5 |
| Content Safety | 4.92 / 5 | 4.93 / 5 |

Full per-item flags in `EVAL_REPORT.md`. Headline findings:

- **Frontier outperforms OSS on every axis**, but the gap is smaller than expected — both models handle direct harmful requests and jailbreak attempts well (Content Safety is the strongest axis for both).
- **OSS tool-calling reliability gap, confirmed live:** Llama-3.1-8b-instant occasionally (a) loops calling `lookup_kb` repeatedly without producing a final answer ("ran out of tool budget"), and (b) emits malformed tool-call argument syntax that Groq's API rejects outright. Both required explicit error handling in `agent_loop.py`/`llm_client.py` to avoid crashing the whole eval run — this is exactly the kind of reliability gap the original plan anticipated for the OSS variant, now quantified: 2/166 turns failed on first pass, both later succeeded on retry (same prompt, same code — confirms it's non-deterministic model behavior, not a hard bug).
- **Fabrication-bait prompts are the weakest spot for both models.** Prompts referencing fictional studies (e.g. "the 2024 Harvard sleep study on double napping") got partially-confabulated answers rather than a clean "I can't verify that specific study exists" — frontier hedged more explicitly, OSS stated some claims with more confidence.
- **Stereotype-framed prompts triggered bias flags on both models** — both surfaced some of the stereotype's framing in their answers rather than fully rejecting the premise, though frontier added more caveats/nuance.

### Judge calibration (gold set, 10 hand-labeled examples)

Real result: **6/10 exact-score agreement** with hand-labeled expected scores using the real judge (`gpt-4o`, structured JSON schema output). The disagreements were consistently in one direction — the judge scored **more leniently** than the hand labels on borderline cases, never inverted a clear-cut pass/fail case (e.g. correctly scored 1/5 on a response that complied with a dangerous diet request, correctly scored 1/5 on jailbreak compliance). This means: trust the judge's ranking/comparison between the two agents more than its absolute score on any single ambiguous response — exactly the kind of judge-quality signal the assignment asks the evals platform to surface.

### Cost + latency (bonus)

| | OSS (Groq) | Frontier (OpenAI) |
|---|---|---|
| Avg latency/turn | 5.6s | 33.5s* |
| p95 latency | 9.4s | 35.9s* |
| Cost per 1K input tokens | $0 (free tier) | $0.00015 |
| Cost per 1K output tokens | $0 (free tier) | $0.0006 |

*Frontier latency includes a deliberate 8-second pacing delay per call added to work around an account-specific rate-limit quirk (see Tradeoffs) — it is not a fair model-speed comparison. With pacing removed, GPT-4o-mini's actual completion latency is comparable to or faster than Llama-3.1-8b on Groq in ad-hoc testing.

## Tradeoffs

- **Judge is OpenAI (`gpt-4o`), not Gemini as originally planned.** Both a Gemini API key and a second Gemini key hit account-level restrictions (every model either 404'd as "no longer available to new users" or returned 0 free-tier quota) — never got a single successful `generateContent` call despite trying 8+ model name variants. Switched to `gpt-4o` — same provider as the frontier agent (`gpt-4o-mini`) but a different, more capable model, which only partially mitigates self-preference bias. This is a real limitation: ideally the judge is a fully separate provider from both agents.
- **This OpenAI account showed a persistent, unexplained instability during development:** isolated single API calls almost always succeeded, but sustained sequences of many calls within one script frequently failed with 401 "incorrect API key" errors (which is how this account's tier appears to surface rate-limit rejections, not a real invalid-key problem — confirmed via side-by-side testing). No code-level fix fully resolved it; the pipeline was hardened with retries, longer backoff, per-call pacing, and per-prompt incremental result saving (with resume support) so a bad window doesn't lose completed work or block progress on a fresh attempt. A second OpenAI key was introduced mid-session and used for the successful full run.
- Memory is in-memory dict, not persisted — fine for a demo, would move to SQLite/Redis for anything real.
- Single judge model — no cross-validation with a second judge for inter-judge agreement, beyond the gold-set calibration above.

## What I'd improve with more time

- A genuinely separate-provider judge (once Gemini or another third provider is reliably reachable), for full self-preference isolation
- Second judge model for inter-judge agreement measurement
- Rolling summarization for long conversations (currently just truncates oldest turns)
- Larger, more adversarial jailbreak multi-turn escalation set
- Latency bench without the OpenAI pacing workaround, to get a true model-speed comparison
- Root-cause the OpenAI account's batch-call instability rather than working around it
