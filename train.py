"""GRPO fine-tuning of Qwen2.5-0.5B-Instruct on GSM8K with Unsloth + TRL.

Unsloth must be imported before trl/transformers so its patches apply.
"""
from unsloth import FastLanguageModel  # noqa: I001

import argparse
import dataclasses
import json
import statistics
import time
from pathlib import Path

from transformers import TrainerCallback
from transformers.trainer_utils import get_last_checkpoint
from trl import GRPOConfig, GRPOTrainer

from data import build_messages, load_gsm8k
from scoring import reward

LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="unsloth/Qwen2.5-0.5B-Instruct")
    p.add_argument("--output_dir", default="outputs/grpo")
    p.add_argument("--run_name", default=None, help="Defaults to the output_dir name")
    p.add_argument("--num_train_examples", type=int, default=2000, help="0 = full train split (7473)")
    p.add_argument("--max_steps", type=int, default=-1, help="-1 = run num_train_epochs")
    p.add_argument("--num_train_epochs", type=float, default=1.0)
    p.add_argument("--num_generations", type=int, default=8)
    p.add_argument("--max_prompt_length", type=int, default=256)
    p.add_argument("--max_completion_length", type=int, default=1024)
    # Effective batch = 32 completions per optimizer step, as in the article (1 x 32).
    # Recent TRL needs the generation batch to be divisible by num_generations; 8 x 4 satisfies
    # this for older TRL versions too. Set 1 x 32 to match the article literally if your TRL allows it.
    p.add_argument("--per_device_train_batch_size", type=int, default=8)
    p.add_argument("--gradient_accumulation_steps", type=int, default=4)
    p.add_argument("--learning_rate", type=float, default=3e-5)
    # The article set neither; these are the TRL defaults of its time (TRL 1.x defaults to 0.0 and "dapo").
    p.add_argument("--beta", type=float, default=0.04)
    p.add_argument("--loss_type", default="grpo")
    p.add_argument("--lora_r", type=int, default=32)
    p.add_argument("--lora_alpha", type=int, default=64)
    p.add_argument("--gpu_memory_utilization", type=float, default=0.8)
    p.add_argument("--save_steps", type=int, default=100)
    p.add_argument("--seed", type=int, default=3407)
    p.add_argument("--report_to", default="none")
    p.add_argument("--resume", action="store_true", help="Resume from the last checkpoint in output_dir")
    p.add_argument("--sample_every", type=int, default=10, help="Dump a sample completion every N reward calls")
    p.add_argument("--timing_skip_steps", type=int, default=5, help="Warm-up steps excluded from step timing")
    return p.parse_args()


class StepTimerCallback(TrainerCallback):
    """Mean step time without warm-up steps, ETA for the run, and a warning on truncated completions."""

    def __init__(self, output_dir: Path, skip_steps: int, clip_threshold: float = 0.05):
        self.output_dir = output_dir
        self.skip_steps = skip_steps
        self.clip_threshold = clip_threshold
        self.durations: list[float] = []
        self._t0 = None

    def on_step_begin(self, args, state, control, **kwargs):
        self._t0 = time.perf_counter()

    def on_step_end(self, args, state, control, **kwargs):
        if self._t0 is not None and state.global_step > self.skip_steps:
            self.durations.append(time.perf_counter() - self._t0)

    def on_log(self, args, state, control, logs=None, **kwargs):
        logs = logs or {}
        for key, value in logs.items():
            if "clipped_ratio" in key and isinstance(value, (int, float)) and value > self.clip_threshold:
                print(f"[warn] step {state.global_step}: {key}={value:.3f} > {self.clip_threshold}")
        if self.durations:
            mean = statistics.mean(self.durations)
            remaining = max(state.max_steps - state.global_step, 0) * mean
            print(f"[timing] step {state.global_step}/{state.max_steps}: "
                  f"mean step {mean:.1f}s, ETA {remaining / 3600:.2f}h, full run {mean * state.max_steps / 3600:.2f}h")

    def on_train_end(self, args, state, control, **kwargs):
        summary = {
            "measured_steps": len(self.durations),
            "skipped_warmup_steps": self.skip_steps,
            "mean_step_s": statistics.mean(self.durations) if self.durations else None,
            "median_step_s": statistics.median(self.durations) if self.durations else None,
            "max_steps": state.max_steps,
            "total_measured_s": sum(self.durations),
        }
        (self.output_dir / "timing.json").write_text(json.dumps(summary, indent=2))


def make_reward_func(samples_path: Path, sample_every: int):
    calls = 0

    def correctness_reward(prompts, completions, answer, **kwargs):
        nonlocal calls
        texts = [c[0]["content"] if isinstance(c, list) else c for c in completions]
        rewards = [reward(t, g) for t, g in zip(texts, answer)]
        if calls % sample_every == 0:
            with samples_path.open("a") as f:
                f.write(json.dumps({"call": calls, "gold": answer[0], "reward": rewards[0],
                                    "completion": texts[0]}, ensure_ascii=False) + "\n")
        calls += 1
        return rewards

    return correctness_reward


def build_grpo_config(args, output_dir: Path) -> GRPOConfig:
    cfg = dict(
        output_dir=str(output_dir),
        run_name=args.run_name or output_dir.name,
        learning_rate=args.learning_rate,
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=0.1,
        warmup_steps=5,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",
        bf16=True,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_generations=args.num_generations,
        beta=args.beta,
        loss_type=args.loss_type,
        max_prompt_length=args.max_prompt_length,
        max_completion_length=args.max_completion_length,
        num_train_epochs=args.num_train_epochs,
        max_steps=args.max_steps,
        save_steps=args.save_steps,
        max_grad_norm=1.0,
        logging_steps=1,
        use_vllm=True,
        seed=args.seed,
        report_to=args.report_to,
        log_completions=True,
    )
    # TRL's GRPOConfig changes between versions; never silently pass unknown fields.
    # Field names supported by the installed TRL version.
    valid = {f.name for f in dataclasses.fields(GRPOConfig)}
    # Requested settings this version doesn't have; passing them would raise TypeError.
    dropped = sorted(set(cfg) - valid)
    if dropped:
        # Training continues without these settings, so the warning is the only trace of the deviation.
        print(f"[warn] GRPOConfig in this TRL version has no fields {dropped}; they are NOT applied. "
              "Record this deviation in REPORT.md.")
    # Build the config from the supported settings only.
    return GRPOConfig(**{k: v for k, v in cfg.items() if k in valid})


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load the base model and its tokenizer.
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        # Must fit the longest prompt plus the longest completion.
        max_seq_length=args.max_prompt_length + args.max_completion_length,
        load_in_4bit=False,  # Keep full-precision weights, no 4-bit quantization.
        fast_inference=True,  # Generate completions with vLLM.
        max_lora_rank=args.lora_r,  # vLLM needs the largest LoRA rank in advance.
        gpu_memory_utilization=args.gpu_memory_utilization,  # GPU memory share reserved by vLLM.
    )
    # Add the trainable LoRA adapter to the base model.
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=LORA_TARGETS,  # Attention and MLP layers that get LoRA weights.
        use_gradient_checkpointing="unsloth",  # Recompute activations in the backward pass to save GPU memory.
        random_state=args.seed,
    )

    # Reproducible random order of the train split.
    ds = load_gsm8k("train").shuffle(seed=args.seed)

    # Keep the first N problems; num_train_examples=0 keeps all of them.
    if args.num_train_examples:
        ds = ds.select(range(min(args.num_train_examples, len(ds))))

    # GRPOTrainer generates from the "prompt" column; "answer" is passed to the reward function.
    ds = ds.map(lambda x: {"prompt": build_messages(x["question"], "paper")})
    n_before = len(ds)

    # Token count of the prompt exactly as the model sees it, with the chat template applied.
    def prompt_len(messages):
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return len(tokenizer(text, add_special_tokens=False)["input_ids"])

    # Drop prompts that exceed the limit, and report how many were removed.
    ds = ds.filter(lambda x: prompt_len(x["prompt"]) <= args.max_prompt_length)
    print(f"Train examples: {len(ds)} (dropped {n_before - len(ds)} prompts longer than {args.max_prompt_length} tokens)")

    # Assemble the trainer: model, data, reward function and step timing.
    config = build_grpo_config(args, output_dir)
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[make_reward_func(output_dir / "samples.jsonl", args.sample_every)],
        args=config,
        train_dataset=ds,
        callbacks=[StepTimerCallback(output_dir, args.timing_skip_steps)],
    )
    # Save the resolved config, including TRL defaults, for the report.
    (output_dir / "grpo_config.json").write_text(trainer.args.to_json_string())

    # With --resume, continue from the last checkpoint; otherwise start from scratch.
    resume = get_last_checkpoint(str(output_dir)) if args.resume else None
    if args.resume and resume is None:
        print("[warn] --resume given but no checkpoint found; starting from scratch")
    trainer.train(resume_from_checkpoint=resume)

    # Save the final adapter and tokenizer; evaluate.py loads this directory for variant C.
    final_dir = output_dir / "lora_final"
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"Saved LoRA adapter to {final_dir}")


if __name__ == "__main__":
    main()
