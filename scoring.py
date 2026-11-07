"""Reward, answer extraction and number normalization. No GPU dependencies."""
import re
from decimal import Decimal, InvalidOperation

# Content of a tag: any text that does not contain another reasoning/validate/answer tag.
# This rejects duplicated or nested tags, which a plain `.+?` inside fullmatch would accept.
_CONTENT = r"(?:(?!</?(?:reasoning|validate|answer)>).)+"

PAPER_FORMAT_RE = re.compile(
    rf"\s*<reasoning>{_CONTENT}</reasoning>\s*"
    rf"<validate>(?P<validate>{_CONTENT})</validate>\s*"
    rf"<answer>(?P<answer>{_CONTENT})</answer>\s*",
    re.DOTALL,
)

# A one-word <validate> ("wait") took over a training run, so a shorter section doesn't count as valid.
# This is a threshold, not a length bonus: more words beyond it earn nothing.
MIN_VALIDATE_WORDS = 10

# Variant A: free-form chain of thought followed by a single <answer> tag at the very end.
_NO_ANSWER_TAG = r"(?:(?!</?answer>).)"
COT_FORMAT_RE = re.compile(
    rf"{_NO_ANSWER_TAG}*<answer>(?P<answer>{_NO_ANSWER_TAG}+)</answer>\s*",
    re.DOTALL,
)

_ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
_NUMBER_RE = re.compile(r"-?\$?\d[\d,]*(?:\.\d+)?")
_WAIT_RE = re.compile(r"\bwait\b", re.IGNORECASE)


def normalize_number(text: str) -> str:
    """'$1,000.00' -> '1000', '-5' -> '-5'. Non-numeric text is returned stripped."""
    s = text.strip().replace(",", "").replace("$", "").strip().rstrip(".")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return s
    if not d.is_finite():
        return s
    return format(d.normalize(), "f")


def answers_match(pred: str | None, gold: str) -> bool:
    return pred is not None and normalize_number(pred) == normalize_number(gold)


def extract_gold(answer_field: str) -> str:
    """GSM8K reference answer is the text after '####'."""
    return answer_field.split("####")[-1].strip()


def strict_answer(response: str, prompt_style: str) -> str | None:
    """Answer from a fully valid structure, else None. prompt_style: 'paper' or 'cot'."""
    pattern = PAPER_FORMAT_RE if prompt_style == "paper" else COT_FORMAT_RE
    match = pattern.fullmatch(response)
    if not match:
        return None
    if prompt_style == "paper" and len(match["validate"].split()) < MIN_VALIDATE_WORDS:
        return None
    return match["answer"].strip()


def soft_answer(response: str) -> str | None:
    """Last <answer> tag (last number inside it, if any); otherwise the last number in the text."""
    tags = _ANSWER_TAG_RE.findall(response)
    if tags:
        content = tags[-1].strip()
        numbers = _NUMBER_RE.findall(content)
        return numbers[-1] if numbers else content
    numbers = _NUMBER_RE.findall(response)
    return numbers[-1] if numbers else None


def has_wait(response: str) -> bool:
    return _WAIT_RE.search(response) is not None


TAGS = ("reasoning", "validate", "answer")
# The base 0.5B model almost never emits the full format, so a strict-only reward yields no
# GRPO signal. Each tag pair earns a little; the total (0.075) stays below wrong-but-formatted (0.1).
PARTIAL_CREDIT_PER_TAG = 0.025


def format_credit(response: str) -> float:
    """Partial reward for tag formatting; the answer itself is not checked.

    Each of <reasoning>, <validate> and <answer> earns PARTIAL_CREDIT_PER_TAG (max 0.075) if:
    - its opening and closing tags each appear exactly once;
    - the opening tag comes before the closing one;
    - the text between them is not blank (<validate> needs MIN_VALIDATE_WORDS words).
    Order between different tags is not checked.
    """
    credit = 0.0
    for tag in TAGS:
        if response.count(f"<{tag}>") != 1 or response.count(f"</{tag}>") != 1:
            continue
        match = re.search(rf"<{tag}>(.*?)</{tag}>", response, re.DOTALL)
        min_words = MIN_VALIDATE_WORDS if tag == "validate" else 1
        if match and len(match[1].split()) >= min_words:
            credit += PARTIAL_CREDIT_PER_TAG
    return credit


def reward(response: str, gold: str) -> float:
    """1.0 correct, 0.1 well-formatted but wrong, <=0.075 partial tags, 0.0 none.

    No length or keyword bonuses.
    """
    pred = strict_answer(response, "paper")
    if pred is None:
        return format_credit(response)
    return 1.0 if answers_match(pred, gold) else 0.1
