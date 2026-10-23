from app.models.workflow import VerificationResult


class QualityGate:
    """A deterministic gate; an agent cannot mark a run successful by itself."""

    minimum_score = 70

    def evaluate(self, verification: dict[str, VerificationResult]) -> tuple[bool, dict[str, list[str]]]:
        repair_items = {}
        for title, result in verification.items():
            issues = []
            # Deterministic check: score must meet minimum
            if result.quality_score < self.minimum_score:
                issues.append(f"Quality score {result.quality_score} below minimum {self.minimum_score}")
            # Deterministic check: must pass verification
            if not result.passed:
                issues.extend(result.issues or ["Verification failed"])
            if issues:
                repair_items[title] = issues
        return not repair_items, repair_items
