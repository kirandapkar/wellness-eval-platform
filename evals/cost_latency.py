"""bonus: cost + latency comparison table. mock mode times the mock calls themselves,
real mode times actual API round-trips - swap MOCK_MODE=false to get real numbers."""
import time
import statistics

from agent.agent_loop import run_turn

# published rates as of this eval run
COST_PER_1K_TOKENS_IN = {"frontier": 0.00015, "oss": 0.0}  # gpt-4o-mini input / groq free tier
COST_PER_1K_TOKENS_OUT = {"frontier": 0.0006, "oss": 0.0}  # gpt-4o-mini output / groq free tier


def bench(variant, n=2):
    latencies = []
    for i in range(n):
        t0 = time.time()
        run_turn(f"bench-{variant}-{i}", "what's a good post-workout snack?", variant)
        latencies.append(time.time() - t0)
    return {
        "variant": variant,
        "avg_latency_s": round(statistics.mean(latencies), 3),
        "p95_latency_s": round(max(latencies), 3),
        "cost_per_1k_input_tokens": COST_PER_1K_TOKENS_IN[variant],
        "cost_per_1k_output_tokens": COST_PER_1K_TOKENS_OUT[variant],
    }


if __name__ == "__main__":
    for v in ["oss", "frontier"]:
        print(bench(v))
