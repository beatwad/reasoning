"""Prompts and GSM8K loading shared by training and evaluation."""
from datasets import load_dataset

from scoring import extract_gold

PAPER_SYSTEM_PROMPT = """Respond in the following format:
<reasoning>
[Break and reason your answer here]
</reasoning>
<validate>
[Criticize your reason and think about it. If you see something start with 'wait']
</validate>
<answer>
[Final integer answer justified by validate]
</answer>"""

# Variant A: ordinary chain-of-thought prompt, final answer in <answer>.
COT_SYSTEM_PROMPT = (
    "Solve the math problem step by step. "
    "At the end, write only the final numeric answer inside <answer></answer> tags, "
    "for example <answer>42</answer>."
)

SYSTEM_PROMPTS = {"paper": PAPER_SYSTEM_PROMPT, "cot": COT_SYSTEM_PROMPT}


def build_messages(question: str, prompt_style: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPTS[prompt_style]},
        {"role": "user", "content": question},
    ]


def load_gsm8k(split: str):
    """Returns a dataset with columns: question, answer (gold number string), answer_raw."""
    ds = load_dataset("openai/gsm8k", "main", split=split)
    return ds.map(
        lambda x: {"answer_raw": x["answer"], "answer": extract_gold(x["answer"])},
    )
