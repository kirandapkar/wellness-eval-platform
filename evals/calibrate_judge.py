"""run judge against hand-labeled gold set, report agreement with expected scores.
skips examples the judge api fails on (rather than aborting the whole run) - real key
observed to intermittently 401 - see README limitations."""
import json
import os

from evals.judge import judge_response

GOLD_PATH = os.path.join(os.path.dirname(__file__), "gold_set", "gold_examples.json")


def calibrate():
    gold = json.load(open(GOLD_PATH))
    hits, total, skipped = 0, 0, 0
    rows = []

    for ex in gold:
        try:
            result = judge_response(ex["prompt"], ex["category"], ex["response"], ex["tool_outputs"])
        except RuntimeError as e:
            print(f"  [SKIP] {ex['id']}: {e}")
            skipped += 1
            continue
        for axis_score in ("hallucination_score", "bias_score", "safety_score"):
            if axis_score not in ex["expected"]:
                continue
            total += 1
            match = result[axis_score] == ex["expected"][axis_score]
            hits += match
            rows.append({"id": ex["id"], "axis": axis_score, "expected": ex["expected"][axis_score],
                         "got": result[axis_score], "match": match})

    print(f"judge agreement: {hits}/{total} = {hits/total:.0%}" if total else "no results scored")
    if skipped:
        print(f"skipped {skipped}/{len(gold)} examples due to api failures")
    for r in rows:
        flag = "OK " if r["match"] else "MISS"
        print(f"  [{flag}] {r['id']} {r['axis']}: expected={r['expected']} got={r['got']}")
    return hits / total if total else 0


if __name__ == "__main__":
    calibrate()
