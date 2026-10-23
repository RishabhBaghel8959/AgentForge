import json

from app.agents.quality_gate import QualityGate
from app.models.workflow import VerificationResult


def _result(passed: bool, score: int, issues: list[str] | None = None) -> VerificationResult:
    return VerificationResult(passed=passed, issues=issues or [], quality_score=score)


def test_gate_passes_when_all_sections_pass():
    gate = QualityGate()
    verification = {
        "Summary": _result(passed=True, score=90),
        "Intro": _result(passed=True, score=85),
    }
    passed, repairs = gate.evaluate(verification)
    assert passed is True
    assert repairs == {}


def test_gate_fails_on_low_score():
    gate = QualityGate()
    verification = {
        "Summary": _result(passed=True, score=50),
    }
    passed, repairs = gate.evaluate(verification)
    assert passed is False
    assert "Summary" in repairs
    assert any("below minimum" in issue for issue in repairs["Summary"])


def test_gate_fails_on_failed_verification():
    gate = QualityGate()
    verification = {
        "Summary": _result(passed=False, score=80, issues=["Missing required content"]),
    }
    passed, repairs = gate.evaluate(verification)
    assert passed is False
    assert "Summary" in repairs
    assert "Missing required content" in repairs["Summary"]


def test_gate_passes_at_minimum_score():
    gate = QualityGate()
    verification = {
        "Summary": _result(passed=True, score=70),
    }
    passed, repairs = gate.evaluate(verification)
    assert passed is True
    assert repairs == {}


def test_gate_collects_issues_from_multiple_sections():
    gate = QualityGate()
    verification = {
        "Summary": _result(passed=True, score=55),
        "Intro": _result(passed=False, score=75, issues=["Empty section"]),
    }
    passed, repairs = gate.evaluate(verification)
    assert passed is False
    assert set(repairs.keys()) == {"Summary", "Intro"}
    assert any("below minimum" in issue for issue in repairs["Summary"])
    assert "Empty section" in repairs["Intro"]