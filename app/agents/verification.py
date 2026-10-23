import json

from app.agents.base import SpecialistAgent
from app.models.workflow import VerificationResult


VERIFY_PROMPT = """
You are the Verification Agent. Check the supplied document section for:
- Relevance to the request
- Instruction compliance (word limit, format, required content)
- Unsupported citations, fabricated statistics, or unsafe output

Fail ONLY for these critical problems:
- Empty or severely incomplete content
- Content unrelated to the section title or request
- Fabricated citations, statistics, or sources
- Unsafe or inappropriate content
- Major instruction violations (e.g., missing required structure, exceeding strict limits)

Do NOT fail for subjective quality issues like clarity, style, or grammar.
Pass normal, relevant, non-empty content that follows the instructions.

Return only JSON: {{"passed":true,"issues":[],"quality_score":0}}.
quality_score should reflect technical correctness (0-100), not subjective polish.
Set passed=false ONLY for the critical problems listed above. Do not rewrite the section.

Request: {request}
Section title: {title}
Section content: {content}
"""


class VerificationAgent(SpecialistAgent):
    name = "verifier"

    def run(self, run_id: str, request: str, title: str, content: str) -> VerificationResult:
        def validate(text: str) -> VerificationResult:
            cleaned = text.replace("```json", "").replace("```", "").strip()
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("Verification response contains no JSON object")
            result = VerificationResult.model_validate(json.loads(cleaned[start:end + 1]))
            # Store verification details in trace for observability
            self.tracer.event(
                run_id, self.name, "verified",
                details={
                    "title": title,
                    "passed": result.passed,
                    "quality_score": result.quality_score,
                    "issues": result.issues,
                },
            )
            return result

        return self.complete(run_id, VERIFY_PROMPT.format(request=request, title=title, content=content), validate)
