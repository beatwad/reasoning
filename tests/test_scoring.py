import pytest

from scoring import extract_gold, has_wait, normalize_number, reward, soft_answer, strict_answer


VALID = "The steps add up and each number matches the problem statement."  # over MIN_VALIDATE_WORDS


def paper(reasoning="r", validate=VALID, answer="42"):
    return (
        f"<reasoning>\n{reasoning}\n</reasoning>\n"
        f"<validate>\n{validate}\n</validate>\n"
        f"<answer>\n{answer}\n</answer>"
    )


def test_correct_answer():
    assert reward(paper(answer="42"), "42") == 1.0


def test_wrong_answer():
    assert reward(paper(answer="41"), "42") == 0.1


def test_no_tags():
    assert reward("The answer is 42", "42") == 0.0


@pytest.mark.parametrize(
    "response,expected",
    [
        ("<reasoning>r</reasoning><answer>42</answer>", 0.05),  # missing validate
        (f"<reasoning>r</reasoning><validate>{VALID}</validate>", 0.05),  # missing answer
        (f"<reasoning>r</reasoning><validate>{VALID}</validate><answer>42", 0.05),  # truncated
        (f"<reasoning></reasoning><validate>{VALID}</validate><answer>42</answer>", 0.05),  # empty tag earns nothing
        ("</reasoning>r<reasoning>", 0.0),  # closed before opened
    ],
)
def test_missing_tags_get_partial_credit(response, expected):
    assert reward(response, "42") == pytest.approx(expected)


def test_wrong_tag_order():
    response = f"<validate>{VALID}</validate><reasoning>r</reasoning><answer>42</answer>"
    assert reward(response, "42") == pytest.approx(0.075)


@pytest.mark.parametrize("answer", ["42", "41"])
def test_one_word_validate_is_not_valid(answer):
    assert strict_answer(paper(validate="wait", answer=answer), "paper") is None
    assert reward(paper(validate="wait", answer=answer), "42") == pytest.approx(0.05)


def test_validate_word_threshold():
    assert reward(paper(validate="word " * 9), "42") == pytest.approx(0.05)
    assert reward(paper(validate="word " * 10), "42") == 1.0


def test_no_bonus_for_longer_validate():
    assert reward(paper(validate="word " * 500), "42") == reward(paper(validate="word " * 10), "42")


def test_validate_threshold_does_not_affect_cot_format():
    assert strict_answer("So 6.\n<answer>6</answer>", "cot") == "6"


@pytest.mark.parametrize(
    "response",
    [
        paper() + "<answer>42</answer>",
        "<reasoning>a</reasoning><reasoning>b</reasoning><validate>v</validate><answer>42</answer>",
        "<reasoning>r</reasoning><validate>v</validate><answer>1</answer><answer>42</answer>",
        "<reasoning>r <answer>42</answer></reasoning><validate>v</validate><answer>42</answer>",
    ],
)
def test_duplicate_tags(response):
    # Not a valid structure, and the duplicated tag itself earns no partial credit.
    assert reward(response, "42") <= 0.05


def test_text_outside_tags_rejected():
    assert reward("Sure! " + paper(), "42") < 0.1
    assert reward(paper() + " Hope this helps", "42") < 0.1


def test_reward_ordering():
    """correct > wrong but formatted > partial tags > nothing, regardless of correctness of partial answers."""
    correct = reward(paper(answer="42"), "42")
    wrong_formatted = reward(paper(answer="41"), "42")
    best_partial = reward(f"<validate>{VALID}</validate><reasoning>r</reasoning><answer>42</answer>", "42")
    one_tag = reward("<reasoning>r</reasoning> 42", "42")
    assert correct > wrong_formatted > best_partial > one_tag > reward("42", "42") == 0.0


@pytest.mark.parametrize("pred,gold", [("1,000", "1000"), ("1000", "1,000"), ("$1,000.00", "1000"), ("12.50", "12.5")])
def test_numbers_with_commas_and_formatting(pred, gold):
    assert reward(paper(answer=pred), gold) == 1.0


def test_negative_numbers():
    assert reward(paper(answer="-5"), "-5") == 1.0
    assert reward(paper(answer="5"), "-5") == 0.1
    assert normalize_number("-1,200") == "-1200"


@pytest.mark.parametrize(
    "wrong_response",
    [
        paper(answer="41"),
        paper(reasoning="wait, but let me rethink " * 200, validate="wait " * 100, answer="41"),
        "wait but rethink 42",
    ],
)
def test_correct_always_beats_wrong(wrong_response):
    correct = paper(reasoning="short", answer="42")
    assert reward(correct, "42") > reward(wrong_response, "42")


def test_no_length_bonus():
    assert reward(paper(reasoning="x " * 2000), "42") == reward(paper(reasoning="x"), "42")


def test_extract_gold():
    assert extract_gold("Some steps <<2*3=6>>\n#### 1,080") == "1,080"


def test_strict_cot_format():
    assert strict_answer("Step 1... so 6.\n<answer>6</answer>", "cot") == "6"
    assert strict_answer("<answer>5</answer> then <answer>6</answer>", "cot") is None
    assert strict_answer("Step 1... so 6.", "cot") is None


def test_soft_answer():
    assert soft_answer("blah <answer>18 dollars</answer>") == "18"
    assert soft_answer("so total is 1,000 and then 7") == "7"
    assert soft_answer("<reasoning>3 + 4 = 7") == "7"  # truncated, falls back to last number
    assert soft_answer("no numbers") is None


def test_has_wait_is_whole_word():
    assert has_wait("Wait, that is wrong")
    assert not has_wait("we await the distribute step")
