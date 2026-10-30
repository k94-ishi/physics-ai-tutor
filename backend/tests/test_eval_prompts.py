import json
from types import SimpleNamespace

from physics_ai_tutor.cli import eval_prompts
from physics_ai_tutor.schemas.ai_review import AiReviewVerdict
from physics_ai_tutor.services import ai_review_service, deepseek_service
from physics_ai_tutor.services.deepseek_service import GenerationResult


def test_golden_set_is_valid_and_balanced():
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)

    assert len(cases) >= 12
    verdicts = {case.expected_verdict for case in cases}
    assert verdicts == {"APPROVE", "EDIT", "REJECT"}
    languages = {case.language.value for case in cases}
    assert languages == {"ja", "en"}
    # Every defective case explains its label and carries a reason code.
    for case in cases:
        if case.expected_verdict != "APPROVE":
            assert case.expected_reasons, case.id
            assert case.note, case.id


def _graded(verdict, reasons=(), confidence=0.9):
    return SimpleNamespace(
        verdict=AiReviewVerdict(verdict) if verdict else None,
        confidence=confidence,
        reasons=list(reasons),
        rationale="x",
        suggested_answer=None,
        rubric=None,
        model="mock",
        prompt_tokens=1,
        completion_tokens=1,
        parsed=verdict is not None,
    )


def _perfect_reviewer(cases):
    by_question = {case.question: case.expected_verdict for case in cases}

    def _grade(question, answer, language, concepts=None, context="", temperature=None):
        assert temperature == 0.0
        return _graded(by_question[question], [])

    return _grade


def test_perfect_reviewer_passes_and_baseline_roundtrips(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    monkeypatch.setattr(ai_review_service, "grade_answer", _perfect_reviewer(cases))

    assert eval_prompts.main(save=True) == 0
    baseline = json.loads(
        (tmp_path / eval_prompts.baseline_path().name).read_text(encoding="utf-8")
    )
    assert baseline["exact_agreement_rate"] == 1.0
    assert baseline["n"] == len(cases)

    assert eval_prompts.main() == 0
    assert "PASS vs baseline" in capsys.readouterr().out


def test_broken_reviewer_fails_against_the_baseline(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)

    monkeypatch.setattr(ai_review_service, "grade_answer", _perfect_reviewer(cases))
    assert eval_prompts.main(save=True) == 0

    # A "broken prompt" that approves everything must be flagged.
    monkeypatch.setattr(
        ai_review_service,
        "grade_answer",
        lambda *args, **kwargs: _graded("APPROVE"),
    )

    assert eval_prompts.main() == 1
    out = capsys.readouterr().out
    assert "FAIL vs baseline" in out
    assert "exact_agreement_rate" in out


def test_missing_baseline_warns_but_passes(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    monkeypatch.setattr(ai_review_service, "grade_answer", _perfect_reviewer(cases))

    assert eval_prompts.main() == 0
    assert "NO BASELINE" in capsys.readouterr().out


def test_dry_run_needs_no_api(monkeypatch, capsys):
    def _forbidden(*args, **kwargs):
        raise AssertionError("dry run must not call the API")

    monkeypatch.setattr(ai_review_service, "grade_answer", _forbidden)
    monkeypatch.setattr(deepseek_service, "generate_answer", _forbidden)

    assert eval_prompts.main(dry_run=True) == 0
    assert "no API calls made" in capsys.readouterr().out


def test_regenerate_uses_the_answer_prompt_at_temperature_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    seen = {"temperatures": set(), "systems": set()}

    def _generate(system_prompt, user_prompt, temperature=None):
        seen["temperatures"].add(temperature)
        seen["systems"].add(system_prompt[:20])
        return GenerationResult(
            content="regenerated", model="mock", prompt_tokens=1, completion_tokens=1
        )

    monkeypatch.setattr(deepseek_service, "generate_answer", _generate)

    captured = {"answers": set()}

    def _grade(question, answer, language, concepts=None, context="", temperature=None):
        captured["answers"].add(answer)
        by_question = {case.question: case.expected_verdict for case in cases}
        return _graded(by_question[question])

    monkeypatch.setattr(ai_review_service, "grade_answer", _grade)

    assert eval_prompts.main(regenerate=True, save=True) == 0
    assert seen["temperatures"] == {0.0}
    assert captured["answers"] == {"regenerated"}


def test_unparsed_verdict_counts_as_disagreement(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    monkeypatch.setattr(
        ai_review_service, "grade_answer", lambda *a, **k: _graded(None)
    )

    assert eval_prompts.main(save=True) == 0
    baseline = json.loads(
        (tmp_path / eval_prompts.baseline_path().name).read_text(encoding="utf-8")
    )
    assert baseline["exact_agreement_rate"] == 0.0
