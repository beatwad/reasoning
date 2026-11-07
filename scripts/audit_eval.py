"""Post-hoc checks of outputs/eval: paired significance, extraction bias, <validate> behaviour.

Usage: python scripts/audit_eval.py [eval_dir]
"""
import json
import math
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scoring import _NUMBER_RE, answers_match, normalize_number  # noqa: E402

BOXED = re.compile(r"\\boxed\{\s*(?:\\text\{)?\\?\$?\s*([-\d,\.]+)")
SECTIONS = re.compile(r"<reasoning>(.*?)</reasoning>\s*<validate>(.*?)</validate>\s*<answer>(.*?)</answer>", re.S)


def careful_answer(text):
    """Answer tag, else last \\boxed{}, else last number; a minus right after a digit is not a sign."""
    tags = re.findall(r"<answer>(.*?)</answer>", text, re.S)
    if tags:
        numbers = _NUMBER_RE.findall(tags[-1])
        return numbers[-1] if numbers else tags[-1].strip()
    boxed = BOXED.findall(text)
    if boxed:
        return boxed[-1]
    numbers = re.findall(r"(?<![\d)])-?\$?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?", text)
    return numbers[-1] if numbers else None


def paired(base, other):
    """Difference with a 95% CI, plus an exact McNemar p-value, for paired correctness."""
    b = sum(x and not y for x, y in zip(base, other))
    c = sum(y and not x for x, y in zip(base, other))
    n = len(base)
    diff = (c - b) / n
    se = math.sqrt(b + c - (c - b) ** 2 / n) / n
    p = min(1, 2 * sum(math.comb(b + c, i) for i in range(min(b, c) + 1)) / 2 ** (b + c))
    return (f"{diff * 100:+.2f} pp, 95% CI [{(diff - 1.96 * se) * 100:+.2f}, {(diff + 1.96 * se) * 100:+.2f}], "
            f"p={p:.3g}, only_base={b}, only_other={c}")


def last_number(text):
    numbers = _NUMBER_RE.findall(text)
    return normalize_number(numbers[-1]) if numbers else None


def main():
    eval_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "outputs/eval")
    preds = {v: [json.loads(line) for line in (eval_dir / v / "predictions.jsonl").open()] for v in "ABC"}
    soft = {v: [r["soft_correct"] for r in p] for v, p in preds.items()}
    careful = {v: [answers_match(careful_answer(r["response"]), r["gold"]) for r in p] for v, p in preds.items()}

    for v, p in preds.items():
        print(f"{v}: soft={st.mean(soft[v]):.4f} careful={st.mean(careful[v]):.4f} "
              f"boxed={st.mean(bool(BOXED.search(r['response'])) for r in p):.3f} "
              f"answer_tag={st.mean('<answer>' in r['response'] and '</answer>' in r['response'] for r in p):.3f}")
    for base, other in [("A", "B"), ("A", "C"), ("B", "C")]:
        print(f"soft    {base}->{other}: {paired(soft[base], soft[other])}")
        print(f"careful {base}->{other}: {paired(careful[base], careful[other])}")

    rows = [(r, m) for r in preds["C"] if (m := SECTIONS.search(r["response"]))]
    same = [(r, m) for r, m in rows if last_number(m[3]) == last_number(m[1])]
    differs = [(r, m) for r, m in rows if last_number(m[3]) != last_number(m[1])]
    print(f"C sections found: {len(rows)}; answer == last number of reasoning: {len(same) / len(rows):.1%}; differs: {len(differs)}")
    print(f"  soft accuracy when same: {st.mean(r['soft_correct'] for r, _ in same):.3f}; "
          f"when differs: {st.mean(r['soft_correct'] for r, _ in differs):.3f}")
    print(f"  reasoning last number wrong, answer right: "
          f"{sum(r['soft_correct'] and not answers_match(last_number(m[1]), r['gold']) for r, m in rows)}")
    print(f"  reasoning last number right, answer wrong: "
          f"{sum(not r['soft_correct'] and answers_match(last_number(m[1]), r['gold']) for r, m in rows)}")
    print(f"  median words: reasoning={st.median(len(m[1].split()) for _, m in rows)} "
          f"validate={st.median(len(m[2].split()) for _, m in rows)}; "
          f"validate under 5 words: {st.mean(len(m[2].split()) < 5 for _, m in rows):.1%}")
    print(f"  validate starts with 'wait': {st.mean(m[2].strip().lower().startswith('wait') for _, m in rows):.1%}")
    print("  top validate openings:", Counter(" ".join(m[2].split()[:5]).lower() for _, m in rows).most_common(6))


if __name__ == "__main__":
    main()
