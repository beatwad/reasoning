"""Builds the metrics table for REPORT.md and dumps example responses.

Usage: python compare.py --eval_dir outputs/eval --examples_variant C --n_examples 10
"""
import argparse
import json
import random
from pathlib import Path

COLUMNS = [
    ("strict_acc", "Strict acc", True),
    ("soft_acc", "Soft acc", True),
    ("format_rate", "Format ok", True),
    ("truncated_rate", "Truncated", True),
    ("mean_len_tokens", "Mean len", False),
    ("median_len_tokens", "Median len", False),
    ("wait_rate", "'wait' rate", True),
    ("soft_acc_with_wait", "Soft acc w/ wait", True),
    ("soft_acc_without_wait", "Soft acc w/o wait", True),
]


def fmt(value, pct: bool) -> str:
    if value is None:
        return "—"
    return f"{100 * value:.2f}%" if pct else f"{value:.1f}"


def load_predictions(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open()]


def paired_counts(a: list[dict], c: list[dict]) -> dict:
    """Per-problem agreement of soft correctness between A and C (inputs for a McNemar test)."""
    pairs = list(zip(a, c))
    assert all(x["idx"] == y["idx"] for x, y in pairs), "prediction files are not aligned"
    return {
        "both_correct": sum(x["soft_correct"] and y["soft_correct"] for x, y in pairs),
        "only_A": sum(x["soft_correct"] and not y["soft_correct"] for x, y in pairs),
        "only_C": sum(y["soft_correct"] and not x["soft_correct"] for x, y in pairs),
        "both_wrong": sum(not x["soft_correct"] and not y["soft_correct"] for x, y in pairs),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--eval_dir", default="outputs/eval")
    p.add_argument("--variants", nargs="+", default=["A", "B", "C"])
    p.add_argument("--examples_variant", default="C")
    p.add_argument("--n_examples", type=int, default=10, help="Per group: correct and incorrect")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    eval_dir = Path(args.eval_dir)

    # Load metrics of the evaluated variants; variants without a metrics file are skipped.
    metrics = {v: json.loads((eval_dir / v / "metrics.json").read_text())
               for v in args.variants if (eval_dir / v / "metrics.json").exists()}
    # Markdown table: header, then one row per variant.
    lines = ["| Variant | n | " + " | ".join(name for _, name, _ in COLUMNS) + " |",
             "|---|---|" + "---|" * len(COLUMNS)]
    for v, m in metrics.items():
        lines.append(f"| {v} | {m['n']} | " + " | ".join(fmt(m[k], pct) for k, _, pct in COLUMNS) + " |")
    # Soft accuracy differences, in percentage points.
    if "A" in metrics and "C" in metrics:
        lines.append(f"\nSoft acc C − A: {100 * (metrics['C']['soft_acc'] - metrics['A']['soft_acc']):+.2f} pp (main metric)")
    if "B" in metrics and "C" in metrics:
        lines.append(f"Soft acc C − B: {100 * (metrics['C']['soft_acc'] - metrics['B']['soft_acc']):+.2f} pp (mostly format effect)")
    # Per-problem A/C comparison: how many problems only one of the variants solved.
    if "A" in metrics and "C" in metrics:
        counts = paired_counts(load_predictions(eval_dir / "A" / "predictions.jsonl"),
                               load_predictions(eval_dir / "C" / "predictions.jsonl"))
        lines.append(f"Paired A/C soft correctness: {counts}")
    # Print the table and save it for REPORT.md.
    table = "\n".join(lines)
    print(table)
    (eval_dir / "metrics_table.md").write_text(table + "\n")

    # Dump example responses of one variant, if its predictions exist.
    preds_path = eval_dir / args.examples_variant / "predictions.jsonl"
    if preds_path.exists():
        preds = load_predictions(preds_path)
        rng = random.Random(args.seed)  # Fixed seed: the same examples on every run.
        out = [f"# Examples, variant {args.examples_variant}\n"]
        # Sample up to n_examples separately from correct and incorrect responses (by soft accuracy).
        for label, group in [("Correct", [r for r in preds if r["soft_correct"]]),
                             ("Incorrect", [r for r in preds if not r["soft_correct"]])]:
            out.append(f"## {label}\n")
            for r in rng.sample(group, min(args.n_examples, len(group))):
                # Heading with the answers and flags, then the question and the raw response.
                out.append(f"### #{r['idx']} gold={r['gold']} soft_pred={r['soft_pred']} "
                           f"format_ok={r['format_ok']} truncated={r['truncated']} wait={r['has_wait']}\n")
                out.append(f"**Q:** {r['question']}\n\n```\n{r['response']}\n```\n")
        path = eval_dir / f"examples_{args.examples_variant}.md"
        path.write_text("\n".join(out))
        print(f"\nExamples written to {path}")


if __name__ == "__main__":
    main()
