"""Greedy evaluation on the GSM8K test split (1319 problems) with vLLM.

Variants:
  A  base model, ordinary CoT prompt with final answer in <answer>
  B  base model, the article's system prompt
  C  fine-tuned LoRA, the article's system prompt (requires --lora)
"""
import argparse
import json
import statistics
from pathlib import Path

from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

from data import build_messages, load_gsm8k
from scoring import answers_match, has_wait, soft_answer, strict_answer

PROMPT_STYLE = {"A": "cot", "B": "paper", "C": "paper"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--variant", choices=["A", "B", "C"], required=True)
    p.add_argument("--model", default="unsloth/Qwen2.5-0.5B-Instruct")
    p.add_argument("--lora", default=None, help="Path to LoRA adapter (variant C)")
    p.add_argument("--max_lora_rank", type=int, default=32)
    p.add_argument("--max_tokens", type=int, default=1024)
    p.add_argument("--max_model_len", type=int, default=2048)
    p.add_argument("--gpu_memory_utilization", type=float, default=0.8)
    p.add_argument("--seed", type=int, default=3407)
    p.add_argument("--limit", type=int, default=0, help="Evaluate only the first N problems (0 = all)")
    p.add_argument("--output_dir", default="outputs/eval")
    p.add_argument("--tag", default=None, help="Subdirectory name, defaults to the variant letter")
    return p.parse_args()


def rate(values) -> float | None:
    values = list(values)
    return sum(values) / len(values) if values else None


def compute_metrics(records: list[dict]) -> dict:
    lengths = [r["num_tokens"] for r in records]
    with_wait = [r for r in records if r["has_wait"]]
    without_wait = [r for r in records if not r["has_wait"]]
    return {
        "n": len(records),
        "strict_acc": rate(r["strict_correct"] for r in records),
        "soft_acc": rate(r["soft_correct"] for r in records),
        "format_rate": rate(r["format_ok"] for r in records),
        "truncated_rate": rate(r["truncated"] for r in records),
        "mean_len_tokens": statistics.mean(lengths),
        "median_len_tokens": statistics.median(lengths),
        "wait_rate": rate(r["has_wait"] for r in records),
        "n_with_wait": len(with_wait),
        "soft_acc_with_wait": rate(r["soft_correct"] for r in with_wait),
        "soft_acc_without_wait": rate(r["soft_correct"] for r in without_wait),
    }


def main():
    args = parse_args()
    if args.variant == "C" and not args.lora:
        raise SystemExit("Variant C requires --lora")
    if args.variant != "C" and args.lora:
        raise SystemExit("--lora is only used for variant C")
    style = PROMPT_STYLE[args.variant]
    out_dir = Path(args.output_dir) / (args.tag or args.variant)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = load_gsm8k("test")
    if args.limit:
        ds = ds.select(range(min(args.limit, len(ds))))

    llm = LLM(
        model=args.model,
        dtype="bfloat16",
        seed=args.seed,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        enable_lora=args.lora is not None,
        max_lora_rank=args.max_lora_rank,
    )
    tokenizer = llm.get_tokenizer()
    prompts = [
        tokenizer.apply_chat_template(build_messages(q, style), tokenize=False, add_generation_prompt=True)
        for q in ds["question"]
    ]
    params = SamplingParams(temperature=0.0, max_tokens=args.max_tokens, seed=args.seed)
    lora_request = LoRARequest("grpo", 1, args.lora) if args.lora else None
    outputs = llm.generate(prompts, params, lora_request=lora_request)

    records = []
    for i, (example, out) in enumerate(zip(ds, outputs)):
        completion = out.outputs[0]
        text = completion.text
        strict_pred = strict_answer(text, style)
        soft_pred = soft_answer(text)
        records.append({
            "idx": i,
            "question": example["question"],
            "gold": example["answer"],
            "response": text,
            "finish_reason": completion.finish_reason,
            "num_tokens": len(completion.token_ids),
            "strict_pred": strict_pred,
            "soft_pred": soft_pred,
            "format_ok": strict_pred is not None,
            "strict_correct": answers_match(strict_pred, example["answer"]),
            "soft_correct": answers_match(soft_pred, example["answer"]),
            "truncated": completion.finish_reason == "length",
            "has_wait": has_wait(text),
        })

    with (out_dir / "predictions.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    metrics = compute_metrics(records)
    metrics["config"] = {**vars(args), "prompt_style": style}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps({k: v for k, v in metrics.items() if k != "config"}, indent=2))


if __name__ == "__main__":
    main()
