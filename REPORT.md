# Report: GRPO on GSM8K (Qwen2.5-0.5B-Instruct)

## Conclusion

**All three GRPO (Group Relative Policy Optimization) runs beat the base model by a modest margin, and none shows learned reasoning. `<validate>` isn't a working check in any run: requiring 10 words removed the one-word exploit, but the model then approved its own answer almost every time, including 95.2% of its wrong answers.** A full epoch isn't justified on this evidence.

| Soft accuracy | A: base, plain prompt | C: trained | C − A | 95% confidence interval (CI) | p |
|---|---|---|---|---|---|
| Run 1: prompt with typo "somethin" | 45.11% | 48.67% | +3.56 percentage points (pp) | +0.83 to +6.30 | 0.013 |
| Run 2: corrected prompt | 45.26% | 50.87% | +5.61 pp | +2.76 to +8.46 | 0.00015 |
| Run 3: corrected prompt, `<validate>` of at least 10 words | 44.96% | 50.72% | +5.76 pp | +3.08 to +8.44 | 0.00003 |

- **Seeds:** run 3's setup was retrained with two more seeds (see [Run 3 with seeds 1 and 2](#run-3-with-seeds-1-and-2)). C scored 50.72%, 50.11% and 48.22% (mean 49.68%, standard deviation (SD) 1.31 pp), and C − A was +5.76, +5.16 and +3.26 pp. The gain is real but smaller than run 3 alone suggests, about +4 to +5 pp. The differences between runs 1–3 are within the seed spread.
- **Accuracy:** the gain over the base model is consistent: every run and every seed is positive. It's far from the article's jump (8.87% → 65.28%): the base model already scores about 45% once the score doesn't depend on the format.
- **Format:** on the article's prompt, strict accuracy went from 0.00% (B) to 48–51% (C). Nearly all of that is format.
- **`<validate>` doesn't explain the gain:** accuracy was practically the same with the single word `wait` (run 2) and with 28-word approvals (run 3). The difference is −0.15 pp (CI −2.78 to +2.47, p=0.955).
- **Limits:** only run 3's setup has more than one seed, and three seeds is still a small sample. Evaluation is also not exactly repeatable (see [Run 2](#run-2-corrected-prompt)).

## Run 1 results (prompt with typo)

GSM8K test set, 1319 problems, greedy decoding, `max_tokens=1024`, seed 3407.

| Variant | Strict acc | Soft acc | Format ok | Truncated | Mean len (tokens) | Median len (tokens) | "wait" rate | Soft acc with "wait" | Soft acc without "wait" |
|---|---|---|---|---|---|---|---|---|---|
| A: base, plain step-by-step prompt | 5.76% | 45.11% | 18.20% | 1.44% | 266.4 | 257.0 | 0.08% | 0.00% | 45.14% |
| B: base, article prompt | 0.00% | 45.34% | 0.00% | 1.90% | 268.1 | 251.0 | 0.15% | 50.00% | 45.33% |
| C: trained, article prompt | 48.37% | 48.67% | 97.42% | 2.58% | 352.9 | 323.0 | 69.22% | 50.16% | 45.32% |

Paired comparisons (95% CI, exact McNemar test):

| Comparison | Soft accuracy | Careful extractor |
|---|---|---|
| A → C (main metric) | +3.56 pp, CI [+0.83, +6.30], p=0.013 | +3.26 pp, CI [+0.53, +5.99], p=0.022 |
| B → C (same prompt) | +3.34 pp, CI [+0.63, +6.04], p=0.018 | +2.50 pp, CI [−0.17, +5.17], p=0.075 |
| A → B (prompt only) | +0.23 pp, CI [−2.42, +2.87], p=0.911 | +0.76 pp, CI [−1.87, +3.39], p=0.612 |

On soft accuracy, A and C differ on 341 problems: 194 solved only by C, 147 only by A. Another 448 are solved by both and 530 by neither.

**Why a second extractor:** C nearly always gives a clean `<answer>` tag, while A and B often fall back to the last number in the text, which can pick the wrong number. The careful extractor also reads `\boxed{}`. It was written after seeing the results, so treat it as a sensitivity check. It closes about 0.8 pp of the gap between B and C and about 0.3 pp between A and C.

## Run 1 exploits and anomalies

Run 2's exploit is described under [Run 2](#run-2-corrected-prompt).

**Partial format credit:** not exploited on the test set, where 97.42% of answers have the full format that earns more than partial credit.

**`<validate>`:** this is the main anomaly. It looks like self-checking, but rarely behaves like it.

- **Stock "wait":** 69.3% of `<validate>` sections open with "wait", even though the reward doesn't pay for the word. The most common opening is "Wait, the question asks for" (327 of 1285).
- **Empty objections:** in the 20 examples below, "wait" usually introduces an objection with no content, such as "the number of chocolate bars in a box is 8, not 8".
- **No real catches in the sample:** none of the 20 `<validate>` sections found and fixed a real error. Several approve a wrong answer or repeat the same mistake.
- **The answer rarely changes:** in 90.1% of structured answers, the final answer equals the last number in `<reasoning>`. Where they differ (127 answers), soft accuracy is lower: 33.1% vs 51.5%.
- **Weak evidence of some benefit:** the answer was right when that last number was wrong 42 times, and the reverse happened 22 times. The last number in `<reasoning>` isn't always its conclusion, so this doesn't show that `<validate>` fixed anything.
- **"Wait" and accuracy:** soft accuracy in C is 50.16% with "wait" and 45.32% without. This is a correlation, and "wait" could simply be more common on easier problems.

**Length:** mean length grew 32% from B to C (268 → 353 tokens) with no length bonus in the reward. The required `<validate>` section, with a median of 41 words, accounts for at least part of this. Sections are not empty: 0.2% of `<validate>` sections are under 5 words.

**Repetition loops:** at least some truncated answers come from the model repeating itself until the token limit (#1060 below). Truncation is low overall, at 2.58%.

## Run 1 examples

20 answers from variant C, sampled with a fixed seed. Full text is in [outputs/eval/examples_C.md](outputs/eval/examples_C.md).

| # | Gold | Answer | What `<validate>` did |
|---|---|---|---|
| 817 | 15 | 15 ✓ | "Wait", then claims the question has a typo; the answer is unchanged |
| 883 | 25 | 25 ✓ | Plain confirmation |
| 84 | 15 | 15 ✓ | Empty objection: "the number of games won is 15, not 15" |
| 553 | 92 | 92 ✓ | Empty objection: "92 additional bottles ... not 92 bottles in total" |
| 1076 | 162 | $162 ✓ | Repeats the calculation and confirms it |
| 1018 | 60 | 60 ✓ | Empty objection, wrongly saying the 18 pages aren't the total |
| 856 | 7 | 7 ✓ | Rejects "7.75 packs", a number never stated in the reasoning |
| 645 | 48 | 48 ✓ | Empty objection, then restates the answer |
| 1002 | 8 | 8 ✓ | Empty objection: "is 8, not 8" |
| 753 | 128 | 128 ✓ | Claims an error, then repeats the same calculation |
| 1166 | 2350 | 2000 ✗ | Replaces one wrong answer (3500) with another that has no real basis |
| 415 | 350 | 365 ✗ | Approves the wrong answer |
| 1006 | 826 | 46937.6 ✗ | Approves an absurd cost for filling a pool |
| 266 | 118000 | −90000 ✗ | "Wait", then explains the wrong result instead of questioning it |
| 554 | 54 | 48 ✗ | Approves the wrong answer in one line |
| 267 | 91 | 43 ✗ | Approves the wrong answer |
| 176 | 100 | 180 ✗ | Blames the problem statement and keeps the wrong answer |
| 1231 | 70 | 75 ✗ | Says "the mean score is not 75", repeats the same mistake, keeps 75 |
| 487 | 4 | 8 ✗ | Approves a calculation that counts meals twice |
| 1060 | 31 | 2 (soft) ✗ | Never reached: `<reasoning>` loops until the token limit |

## Run 2: corrected prompt

Same code and settings as run 1, with only the prompt typo corrected. Outputs are in `outputs/grpo_2k_fixed_prompt/` and `outputs/eval_fixed_prompt/`.

| Variant | Strict acc | Soft acc | Format ok | Truncated | Mean len (tokens) | Median len (tokens) | "wait" rate | Soft acc with "wait" | Soft acc without "wait" |
|---|---|---|---|---|---|---|---|---|---|
| A: base, plain step-by-step prompt | 5.38% | 45.26% | 18.12% | 1.74% | 268.6 | 259.0 | 0.08% | 0.00% | 45.30% |
| B: base, article prompt | 0.00% | 43.67% | 0.00% | 1.67% | 266.4 | 247.0 | 0.30% | 50.00% | 43.65% |
| C: trained, article prompt | 50.72% | 50.87% | 98.56% | 1.36% | 214.5 | 188.0 | 98.56% | 51.46% | 10.53% |

| Comparison | Soft accuracy | Careful extractor |
|---|---|---|
| A → C (main metric) | +5.61 pp, CI [+2.76, +8.46], p=0.00015 | +5.38 pp, CI [+2.54, +8.23], p=0.00027 |
| B → C (same prompt) | +7.20 pp, CI [+4.45, +9.95], p<0.00001 | +6.52 pp, CI [+3.79, +9.25], p<0.00001 |
| A → B (prompt only) | −1.59 pp, CI [−4.27, +1.09], p=0.267 | −1.14 pp, CI [−3.82, +1.54], p=0.437 |

**Exploit: `<validate>` is one word.** In all 1300 structured test answers, the section is exactly `wait`, for both correct and wrong answers:

```
<validate>
wait
</validate>
```

- **Onset:** every sampled training completion from reward call 30 to the end of training has this `<validate>` (47 samples). Run 1 never did this on the test set (0 of 1285).
- **Why the reward allows it:** the format check only needs non-blank content, and the prompt mentions "wait". The doc's original regex would accept this too. So it's a gap in the format check, separate from partial credit.
- **Length:** mean length fell to 214.5 tokens, compared with 352.9 in run 1. Median `<reasoning>` fell to 102 words from 149. Whether the shorter text comes from the prompt, the length bias of the `grpo` loss, or chance wasn't tested.
- **"Wait" statistics are meaningless here:** the 10.53% "without wait" group is the 19 unformatted answers, 18 of which were truncated.

**Evaluation isn't exactly repeatable.** Variant A's prompt and seed were the same in both runs, yet 767 of 1319 responses differ, typically starting partway through the text. The correct/incorrect result changed on 124 problems (63 gained, 61 lost), while overall accuracy moved only 0.15 pp. The cause wasn't established. So exact per-problem results shouldn't be expected to match between runs, and small accuracy differences should be read with this in mind.

**Training:** 2.27 s per step, 18.7 min of measured steps. Reward reached about 0.63 in the last 100 steps. Truncation averaged 0.31%, with 4 of 499 steps over 5% (maximum 9.4%).

## Run 3: `<validate>` of at least 10 words

Same settings as run 2, with `<validate>` required to have at least 10 words for both the full format and partial credit. Outputs are in `outputs/grpo_2k_min_validate/` and `outputs/eval_min_validate/`.

| Variant | Strict acc | Soft acc | Format ok | Truncated | Mean len (tokens) | Median len (tokens) | "wait" rate | Soft acc with "wait" | Soft acc without "wait" |
|---|---|---|---|---|---|---|---|---|---|
| A: base, plain step-by-step prompt | 5.69% | 44.96% | 18.65% | 1.52% | 269.5 | 258.0 | 0.08% | 0.00% | 44.99% |
| B: base, article prompt | 0.00% | 45.56% | 0.00% | 1.82% | 263.7 | 245.0 | 0.23% | 33.33% | 45.59% |
| C: trained, article prompt | 50.04% | 50.72% | 97.12% | 1.82% | 311.2 | 288.0 | 0.38% | 60.00% | 50.68% |

| Comparison | Soft accuracy | Careful extractor |
|---|---|---|
| A → C (main metric) | +5.76 pp, CI [+3.08, +8.44], p=0.00003 | +5.53 pp, CI [+2.86, +8.20], p=0.00006 |
| B → C (same prompt) | +5.16 pp, CI [+2.50, +7.82], p=0.00019 | +4.62 pp, CI [+1.97, +7.28], p=0.00079 |
| A → B (prompt only) | +0.61 pp, CI [−2.08, +3.30], p=0.699 | +0.91 pp, CI [−1.80, +3.62], p=0.546 |

Compared with the other C results, run 3's soft accuracy differs by +2.05 pp from run 1 (CI −0.46 to +4.55, p=0.123) and −0.15 pp from run 2 (CI −2.78 to +2.47, p=0.955).

**The one-word exploit is gone, replaced by automatic approval.** Sections now have a median of 28 words, all 1295 are different, and no section is padded with repeated "wait". But the content rarely checks anything:

| Structured answers in C | Run 1 | Run 3 |
|---|---|---|
| `<validate>` opens with "the ... is correct": all answers | 24.1% | 96.9% |
| Same, wrong answers only | 23.6% | 95.2% |
| Contains a doubt word (such as "wrong", "error", "however"): wrong answers | 18.9% | 2.1% |

- **Typical section:** "The calculation is correct. The total number of lions in the enclosure is 32." Most sections approve the answer and then restate it.
- **Measurement:** these rates come from simple text patterns, so they're approximate. The approval rate is in `outputs/eval_min_validate/audit.txt`. The doubt-word row was a one-off check, not saved to a file.
- **"Wait":** it nearly disappeared (0.38%), even though the prompt suggests it. In run 2 it filled the section. So the word tracks what's cheapest to pass the check, not actual doubt.
- **Why the reward allows it:** the reward can check the structure and the final answer, but not whether a check took place. A longer minimum would most likely produce longer approvals.

**Evaluation repeatability, again:** variant A's responses were identical to run 2's on only 545 of 1319 problems, and the correct/incorrect result changed on 118.

**Training:** 2.78 s per step, 22.9 min of measured steps. Reward reached about 0.58 in the last 100 steps. Truncation averaged 0.30%, with 4 of 499 steps over 5% (maximum 6.25%).

## Run 3 with seeds 1 and 2

Run 3's setup was trained twice more with `--seed 1` and `--seed 2`. The training seed sets both the LoRA initialization and the shuffle, so each seed also trains on a different 2000 problems. All three C adapters were evaluated with the same evaluation seed (3407) and compared with run 3's A and B. Outputs are in `outputs/grpo_2k_min_validate_s{1,2}/` and `outputs/eval_min_validate/C_s{1,2}/`, and audits are in `outputs/eval_min_validate/audit_s{1,2}.txt`.

| Training seed | Strict acc | Soft acc | Format ok | Truncated | Mean len (tokens) | A → C (soft) | B → C (soft) |
|---|---|---|---|---|---|---|---|
| 3407 (run 3) | 50.04% | 50.72% | 97.12% | 1.82% | 311.2 | +5.76 pp, CI [+3.08, +8.44], p=0.00003 | +5.16 pp, p=0.00019 |
| 1 | 49.73% | 50.11% | 98.33% | 0.91% | 285.8 | +5.16 pp, CI [+2.37, +7.95], p=0.00037 | +4.55 pp, p=0.0016 |
| 2 | 48.07% | 48.22% | 98.79% | 1.14% | 258.7 | +3.26 pp, CI [+0.43, +6.09], p=0.027 | +2.65 pp, p=0.066 |
| **Mean ± SD across seeds** | | **49.68% ± 1.31 pp** | | | | **+4.73 pp** | **+4.12 pp** |

- **The gain over the base model survives a seed change.** Every seed beats A, and two of the three are clearly significant. Across seeds, C − A runs from +3.3 to +5.8 pp, so the run-3 figure of +5.76 pp is at the top of that range. A fair estimate of the gain is about +4 to +5 pp.
- **Seed-to-seed spread is comparable to the differences between runs 1–3.** The C pairs differ by −0.61 pp (3407 → 1, p=0.69), −2.50 pp (3407 → 2, p=0.068) and −1.90 pp (1 → 2, p=0.16). So the gap between run 1 (48.67%) and runs 2–3 (about 50.8%) can't be credited to the prompt fix or the 10-word rule. It is within this spread.
- **`<validate>` is still automatic approval.** It opens with "the ... is correct" in 95.6% of seed 1's wrong answers and 83.4% of seed 2's. Seed 2's figure understates it: its third most common opening, "this calculation is correct because", doesn't match the pattern. The median section is 39 words for both seeds.
- **Training:** 2.93 s and 2.64 s per step. The `clipped_ratio` warning (over 5%) fired on 10 and 7 steps, maximum 9.4% for both. Seed 1 kept all 2000 problems (500 steps), and seed 2 dropped 2 (499 steps).

## Configuration

- **Model:** `unsloth/Qwen2.5-0.5B-Instruct`, bf16, LoRA `r=32`, `lora_alpha=64`.
- **Data:** first 2000 problems of the GSM8K train split after shuffling with seed 3407. 2 prompts over 256 tokens were dropped, leaving 1,998 problems and 499 steps.
- **Training:** `num_generations=8`, `max_completion_length=1024`, `learning_rate=3e-5`, 1 epoch.
- **Reward:** 1.0 for correct and fully formatted, 0.1 for fully formatted but wrong, 0.025 per valid tag pair otherwise (maximum 0.075), and 0 with no valid tag pairs. Run 3 also requires at least 10 words in `<validate>`.
- **Full settings:** [outputs/grpo_2k/grpo_config.json](outputs/grpo_2k/grpo_config.json).
- **Environment:** RTX 4090, Python 3.12.7, unsloth 2026.11.2, trl 1.15.0, vllm 0.33.0, peft 0.21.2, transformers 5.17.0, torch 2.14.0. Everything else is in [versions.txt](versions.txt).

### Deviations from the plan and the article

| Item | Plan or article | This run | Reason |
|---|---|---|---|
| Reward | Strict only: 1.0 / 0.1 / 0.0 | Added partial format credit | Strict-only reward was 0 at every step, so GRPO had no signal |
| Tag regex | `.+?` inside `fullmatch` | Tag content can't contain another tag | The original accepts duplicate tags |
| Number comparison | Remove `,` and `$`, then compare text | Also compares numeric value (`12.50` = `12.5`) | Avoids false mismatches |
| Batch | 1 × 32 | 8 × 4 (same 32 completions per step) | Generation batch must divide by `num_generations` |
| `max_seq_length` | 1024 | 1280 | Must fit a 256-token prompt plus a 1024-token completion |
| `max_prompt_length` | 256 | Not passed | Removed in TRL 1.15; `train.py` filters long prompts instead |
| `beta`, `loss_type` | Not set in the article | `0.04`, `grpo` | Believed to match the TRL defaults of the article's time; TRL 1.15 defaults to `0.0`, `dapo` |
| `temperature` | Not set in the article | 1.0 (TRL 1.15 default) | The article-era default may differ; not verified |
| Full epoch (plan step 6) | Run if accuracy grows and no exploits | Not run | Exploit in run 2, reward plateau, questionable `<validate>` in run 1 |
| SVAMP or MathQA check | Optional | Not run | Optional |

### Why partial credit was needed

With the article's prompt, the base model almost never produces the format. It produced 0 fully formatted answers in the 320 completions of a 10-step strict-reward run (that run's outputs weren't kept), and 0.00% in variant B on the full test set.

A separate probe on 100 test problems tried the bnb-4bit repo and the article's exact prompt whitespace. Neither helped: full format stayed at 0%, and any tag appeared in only 1.5–2.5% of samples at temperature 1.0. Moving the instructions to the user turn or adding a one-shot example gave at most 0.5% (100 train problems). The probe scripts weren't kept, so these probe numbers can't be regenerated from saved files.

The article avoided this because its reward paid for any single tag pair plus length, even with a wrong answer. Its 8.87% baseline couldn't be reproduced with the prompt it shows. The author mentions the model repeating a "one-shot example", and that prompt has none, so the evaluation prompt may have been different.

## Run 1 training and time

Reward over the run (means per 50-step window):

| Steps | Reward | Mean length (tokens) | Truncated |
|---|---|---|---|
| 1–50 | 0.187 | 217 | 0.4% |
| 51–100 | 0.501 | 292 | 3.4% |
| 101–150 | 0.463 | 384 | 0.9% |
| 151–200 | 0.529 | 333 | 0.1% |
| 201–250 | 0.575 | 334 | 0.1% |
| 251–300 | 0.572 | 387 | 0.4% |
| 301–350 | 0.566 | 377 | 1.1% |
| 351–400 | 0.536 | 371 | 0.6% |
| 401–450 | 0.587 | 361 | 0.4% |
| 451–499 | 0.575 | 346 | 0.4% |

Reward levels off from about step 200.

**Truncation during training:** 0.78% on average, under the plan's 5% limit. The limit was exceeded on 17 of 499 individual steps, with a maximum of 28%, so these are isolated spikes. The cause of the spikes wasn't investigated.

| Stage | Mean step | Steps | Time |
|---|---|---|---|
| Smoke run (`beta=0`, `dapo`) | 1.84 s | 75 | 129 s of measured steps |
| Main run, 1,998 problems | 2.88 s | 499 | 23.7 min of measured steps, excluding model loading and the first 5 steps |
| Full epoch | not run | about 1868 | about 1.5 h estimated |
| Evaluation A / B / C | n/a | n/a | about 53 s / 52 s / 76 s, including model loading |

## Reproducing the results

Commands are in [README.md](README.md). This run used:

```bash
python train.py --output_dir outputs/grpo_2k --num_train_examples 2000
python evaluate.py --variant A
python evaluate.py --variant B
python evaluate.py --variant C --lora outputs/grpo_2k/lora_final
python compare.py --examples_variant C --n_examples 10
python scripts/audit_eval.py
```

Run 1 used the prompt with the typo "If you see somethin start with 'wait'", and `data.py` has since been corrected to "something". Run 2 used the same commands with `--output_dir outputs/grpo_2k_fixed_prompt` and `--output_dir outputs/eval_fixed_prompt`.

**Only run 3 matches the current code,** using the same commands with `--output_dir outputs/grpo_2k_min_validate` and `--output_dir outputs/eval_min_validate`. Runs 1 and 2 predate the 10-word rule, and their numbers use the earlier check. Rerunning `evaluate.py` on run 2's adapter would no longer count its one-word `<validate>` answers as correctly formatted. Exact responses also differ between runs (see [Run 2](#run-2-corrected-prompt)).

The extra seeds used `--seed 1` / `--seed 2` with `--output_dir outputs/grpo_2k_min_validate_s{1,2}`, then `python evaluate.py --variant C --lora outputs/grpo_2k_min_validate_s{1,2}/lora_final --output_dir outputs/eval_min_validate --tag C_s{1,2}`. To audit them, `scripts/audit_eval.py` needs a directory where `A` and `B` link to run 3's and `C` links to `C_s1` or `C_s2`.

## Raw outputs

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Predictions | `outputs/eval/{A,B,C}/predictions.jsonl` | `outputs/eval_fixed_prompt/{A,B,C}/predictions.jsonl` | `outputs/eval_min_validate/{A,B,C}/predictions.jsonl` |
| Metrics table, audit, examples | `outputs/eval/` | `outputs/eval_fixed_prompt/` | `outputs/eval_min_validate/` |
| Adapter and checkpoints | `outputs/grpo_2k/` | `outputs/grpo_2k_fixed_prompt/` | `outputs/grpo_2k_min_validate/` |
| Training log | `logs/train_grpo_2k.log` | `logs/train_grpo_2k_fixed_prompt.log` | `logs/train_grpo_2k_min_validate.log` |
| Seeds 1, 2 | | | `outputs/eval_min_validate/C_s{1,2}/`, `outputs/grpo_2k_min_validate_s{1,2}/`, `logs/*_s{1,2}.log` |
