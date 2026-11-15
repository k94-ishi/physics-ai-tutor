import json
from types import SimpleNamespace

from physics_ai_tutor.cli import eval_prompts
from physics_ai_tutor.schemas.ai_review import AiReviewVerdict
from physics_ai_tutor.services import ai_review_service
from physics_ai_tutor.services.deepseek_service import GenerationResult
from tests.conftest import patch_generation


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


def _patch_grade(monkeypatch, grade):
    """Install one plain sync stub on the async grading seam ([106])."""

    async def _async_grade(*args, **kwargs):
        return grade(*args, **kwargs)

    monkeypatch.setattr(ai_review_service, "async_grade_answer", _async_grade)


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
    # Production cases can share a question (pre-edit and approved texts of
    # the same row), so key on the full pair.
    by_pair = {(case.question, case.answer): case.expected_verdict for case in cases}

    def _grade(question, answer, language, concepts=None, context="", **kwargs):
        assert kwargs.get("temperature") == 0.0
        return _graded(by_pair[(question, answer)], [])

    return _grade


def test_perfect_reviewer_passes_and_baseline_roundtrips(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    _patch_grade(monkeypatch, _perfect_reviewer(cases))

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

    _patch_grade(monkeypatch, _perfect_reviewer(cases))
    assert eval_prompts.main(save=True) == 0

    # A "broken prompt" that approves everything must be flagged.
    _patch_grade(monkeypatch, lambda *args, **kwargs: _graded("APPROVE"))

    assert eval_prompts.main() == 1
    out = capsys.readouterr().out
    assert "FAIL vs baseline" in out
    assert "exact_agreement_rate" in out


def test_reject_recall_collapse_is_gated(monkeypatch, tmp_path, capsys):
    """A reviewer that keeps its precision but stops rejecting must fail.

    This is the v3/r2 shape: recall fell 0.385 -> 0.231 while the gated
    metrics stayed inside tolerance, so the regression went unnoticed.
    """
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    _patch_grade(monkeypatch, _perfect_reviewer(cases))
    assert eval_prompts.main(save=True) == 0

    # Perfect except that most rejects are downgraded to EDIT: precision
    # stays 1.0 (every reject it does make is right) but recall collapses.
    perfect = _perfect_reviewer(cases)
    seen = {"n": 0}

    def _shy_about_rejecting(question, answer, language, **kwargs):
        graded = perfect(question, answer, language, **kwargs)
        if graded.verdict == AiReviewVerdict.REJECT:
            seen["n"] += 1
            if seen["n"] > 2:
                return _graded("EDIT", [])
        return graded

    _patch_grade(monkeypatch, _shy_about_rejecting)

    assert eval_prompts.main() == 1
    assert "reject_recall" in capsys.readouterr().out


def test_missing_baseline_warns_but_passes(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    _patch_grade(monkeypatch, _perfect_reviewer(cases))

    assert eval_prompts.main() == 0
    assert "NO BASELINE" in capsys.readouterr().out


def test_dry_run_needs_no_api(monkeypatch, capsys):
    def _forbidden(*args, **kwargs):
        raise AssertionError("dry run must not call the API")

    _patch_grade(monkeypatch, _forbidden)
    patch_generation(monkeypatch, _forbidden)

    assert eval_prompts.main(dry_run=True) == 0
    assert "no API calls made" in capsys.readouterr().out


def test_regenerate_uses_the_answer_prompt_at_temperature_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    cases = eval_prompts.load_golden_set(eval_prompts.DEFAULT_SET)
    seen = {"temperatures": set(), "systems": set()}

    def _generate(system_prompt, user_prompt, temperature=None, **kwargs):
        seen["temperatures"].add(temperature)
        seen["systems"].add(system_prompt[:20])
        return GenerationResult(
            content="regenerated", model="mock", prompt_tokens=1, completion_tokens=1
        )

    patch_generation(monkeypatch, _generate)

    captured = {"answers": set()}

    def _grade(question, answer, language, concepts=None, context="", **kwargs):
        captured["answers"].add(answer)
        # Regenerated answers do not match stored ones; verdict by question
        # is enough here since only the plumbing is under test.
        by_question = {case.question: case.expected_verdict for case in cases}
        return _graded(by_question[question])

    _patch_grade(monkeypatch, _grade)

    assert eval_prompts.main(regenerate=True, save=True) == 0
    assert seen["temperatures"] == {0.0}
    assert captured["answers"] == {"regenerated"}


def test_unparsed_verdict_counts_as_disagreement(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_prompts, "EVAL_DIR", tmp_path)
    _patch_grade(monkeypatch, lambda *a, **k: _graded(None))

    assert eval_prompts.main(save=True) == 0
    baseline = json.loads(
        (tmp_path / eval_prompts.baseline_path().name).read_text(encoding="utf-8")
    )
    assert baseline["exact_agreement_rate"] == 0.0
