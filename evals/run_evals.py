"""orchestrate: call both agents on the dataset, judge each response, dump raw results."""
import argparse
import json
import os
import uuid

from agent.agent_loop import run_turn
from evals.judge import judge_response

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset", "prompts.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")


def run_one(prompt_obj, variant):
    session_id = str(uuid.uuid4())
    turns = [prompt_obj["prompt"]]
    if prompt_obj.get("follow_up"):
        turns.append(prompt_obj["follow_up"])
    if prompt_obj.get("follow_up_2"):
        turns.append(prompt_obj["follow_up_2"])

    turn_results = []
    for turn_text in turns:
        try:
            result = run_turn(session_id, turn_text, variant)
            scores = judge_response(turn_text, prompt_obj["category"], result["reply"], result["tool_calls"])
        except RuntimeError as e:
            turn_results.append({"prompt": turn_text, "error": str(e)})
            continue
        turn_results.append({
            "prompt": turn_text,
            "response": result["reply"],
            "tool_calls": result["tool_calls"],
            "scores": scores,
        })
    return turn_results


def run_evals(agents, limit=None, resume=True):
    dataset = json.load(open(DATASET_PATH))
    if limit:
        dataset = dataset[:limit]

    results = {agent: [] for agent in agents}
    done_ids = {agent: set() for agent in agents}
    if resume and os.path.exists(RESULTS_PATH):
        existing = json.load(open(RESULTS_PATH))
        for agent in agents:
            if agent in existing:
                # only skip items that fully succeeded - items with error turns get retried
                clean = [item for item in existing[agent] if not any("error" in t for t in item["turns"])]
                errored = [item for item in existing[agent] if any("error" in t for t in item["turns"])]
                results[agent] = clean
                done_ids[agent] = {item["id"] for item in clean}
                if errored:
                    print(f"  {agent}: retrying {len(errored)} previously-errored item(s): {[i['id'] for i in errored]}")

    for agent in agents:
        failed = sum(1 for item in results[agent] for t in item["turns"] if "error" in t)
        skipped = 0
        for i, p in enumerate(dataset):
            if p["id"] in done_ids[agent]:
                skipped += 1
                continue
            try:
                turns = run_one(p, agent)
            except Exception as e:
                turns = [{"prompt": p["prompt"], "error": f"unhandled: {e}"}]
            results[agent].append({"id": p["id"], "category": p["category"], "turns": turns})
            failed += sum(1 for t in turns if "error" in t)
            json.dump(results, open(RESULTS_PATH, "w"), indent=2)  # save after every single prompt
            print(f"  {agent}: {i + 1}/{len(dataset)} ({p['id']}) done ({failed} turn errors so far)")
        print(f"done: {agent} ({len(dataset)} prompts, {skipped} resumed/skipped, {failed} turn errors)")

    print(f"wrote {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["oss", "frontier", "both"], default="both")
    ap.add_argument("--limit", type=int, default=None, help="only run first N prompts, for quick testing")
    ap.add_argument("--no-resume", action="store_true", help="ignore existing results.json, start fresh")
    args = ap.parse_args()
    agents = ["oss", "frontier"] if args.agent == "both" else [args.agent]
    run_evals(agents, limit=args.limit, resume=not args.no_resume)
