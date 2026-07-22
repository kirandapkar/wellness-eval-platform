"""aggregate results.json into per-agent per-axis scores + a comparison chart."""
import json
import os

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "EVAL_REPORT.md")

AXES = ["hallucination_score", "bias_score", "safety_score"]


def aggregate(results):
    agg = {}
    for agent, items in results.items():
        sums = {axis: 0 for axis in AXES}
        counts = {axis: 0 for axis in AXES}
        flags = {axis.replace("_score", "_flags"): [] for axis in AXES}
        errors = 0

        for item in items:
            for turn in item["turns"]:
                if "error" in turn:
                    errors += 1
                    continue
                s = turn["scores"]
                for axis in AXES:
                    sums[axis] += s[axis]
                    counts[axis] += 1
                for flag_key in flags:
                    for f in s.get(flag_key, []):
                        flags[flag_key].append({"id": item["id"], "flag": f})

        agg[agent] = {
            "avg": {axis: round(sums[axis] / counts[axis], 2) if counts[axis] else None for axis in AXES},
            "flags": flags,
            "errors": errors,
        }
    return agg


def write_report(agg):
    lines = ["# Wellness Assistant — Eval Report\n"]
    lines.append("| Axis | " + " | ".join(agg.keys()) + " |")
    lines.append("|---|" + "---|" * len(agg))
    axis_labels = {"hallucination_score": "Hallucination", "bias_score": "Bias & Harmful", "safety_score": "Content Safety"}
    for axis in AXES:
        row = [axis_labels[axis]] + [str(agg[agent]["avg"][axis]) for agent in agg]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n## Flagged issues\n")
    for agent in agg:
        lines.append(f"### {agent}" + (f" ({agg[agent]['errors']} turns skipped due to api errors)" if agg[agent]["errors"] else ""))
        for flag_key, items in agg[agent]["flags"].items():
            if items:
                lines.append(f"**{flag_key}** ({len(items)}):")
                for it in items[:10]:
                    lines.append(f"- {it['id']}: {it['flag']}")
        lines.append("")

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    results = json.load(open(RESULTS_PATH))
    agg = aggregate(results)
    print(json.dumps(agg, indent=2))
    write_report(agg)
