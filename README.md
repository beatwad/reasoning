# GRPO on GSM8K: reproduction with a fixed reward

Checks whether GRPO improves Qwen2.5-0.5B-Instruct on GSM8K beyond the format-learning effect.
Task spec: [grpo-gsm8k-task.md](grpo-gsm8k-task.md).

## Files

| File | Purpose |
|---|---|
| `scoring.py` | Reward (1.0 / 0.1 / 0.0), number normalization, strict/soft answer extraction, `wait` detection |
| `data.py` | System prompts (article prompt, plain CoT prompt) and GSM8K loading |
| `train.py` | GRPO + LoRA training (Unsloth + TRL + vLLM), resumable, step timing |
| `evaluate.py` | Greedy vLLM eval on the 1319 test problems, variants A/B/C → `predictions.jsonl`, `metrics.json` |
| `compare.py` | Metrics table, C−A / C−B deltas, paired A/C counts, sample responses |
| `scripts/audit_eval.py` | Paired significance tests, extraction-bias check, `<validate>` statistics |
| `tests/test_scoring.py` | Reward unit tests |
| `scripts/record_env.sh` | Writes GPU info and exact package versions to `versions.txt` |

## Commands

```bash
# 1. Environment
pip install -r requirements.txt
bash scripts/record_env.sh            # -> versions.txt
nvidia-smi

# 2. Reward tests (must pass before any training)
pytest

# 3. Smoke run: 75 steps; check loss, reward, samples.jsonl, [timing] lines, clipped_ratio
python train.py --output_dir outputs/smoke --num_train_examples 2000 --max_steps 75

# 4. Main run on 2000 problems
python train.py --output_dir outputs/grpo_2k --num_train_examples 2000
#    resume after an interruption:
python train.py --output_dir outputs/grpo_2k --num_train_examples 2000 --resume

# 5. Full epoch (only if step 4 improves accuracy without exploits)
python train.py --output_dir outputs/grpo_full --num_train_examples 0

# 6. Evaluation (same token limit and seed for all variants)
python evaluate.py --variant A
python evaluate.py --variant B
python evaluate.py --variant C --lora outputs/grpo_2k/lora_final
#    evaluate an intermediate checkpoint:
python evaluate.py --variant C --lora outputs/grpo_2k/checkpoint-100 --tag C_ckpt100

# 7. Table + examples for REPORT.md
python compare.py --examples_variant C --n_examples 10
python scripts/audit_eval.py | tee outputs/eval/audit.txt
```

Each `train.py` output directory holds: `checkpoint-*` (LoRA + optimizer state, every 100 steps),
`lora_final/`, `grpo_config.json` (resolved config), `timing.json`, `samples.jsonl` (sampled completions with rewards).

## Differences from the article's recipe

- Reward replaced: no length bonus, no `wait/but/rethink` multiplier. Tags must appear once each, in order, with nothing outside them.
- Partial format credit, 0.025 per tag pair (max 0.075, below the 0.1 for wrong-but-formatted). The base model produced 0% fully formatted answers in the probes (greedy and T=1.0), so a strict-only reward gave GRPO zero signal.
- `<validate>` must have at least 10 words (`MIN_VALIDATE_WORDS`) to count, both for the full format and for partial credit. In one run, the model reduced it to the single word `wait`. This is a threshold, with no bonus for extra words. Runs 1 and 2 in `REPORT.md` predate this rule.
- `num_generations=8`, `max_completion_length=1024` (article: 2 and 512).
- `max_seq_length = max_prompt_length + max_completion_length = 1280` (article: 1024, which can't hold a 256-token prompt plus a 1024-token completion).
- Batch is `8 × 4` instead of `1 × 32`. That's still 32 completions per optimizer step, but the generation batch now divides by `num_generations`, as TRL requires. Use `--per_device_train_batch_size 1 --gradient_accumulation_steps 32` if your TRL version accepts it.
- Model is `unsloth/Qwen2.5-0.5B-Instruct` in bf16 (`load_in_4bit=False`), not the bnb-4bit repo.
- `beta=0.04` and `loss_type="grpo"` are set explicitly to match the TRL defaults of the article's time (TRL 1.x defaults to 0.0 and `dapo`). Other settings, such as `temperature`, use the installed TRL defaults. All resolved values are in `grpo_config.json`.
- `train.py` prints a warning if a recipe field doesn't exist in the installed `GRPOConfig`. Any such warning is a deviation and goes in the report.
