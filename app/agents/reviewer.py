from app.agents.base import SpecialistAgent
from app.utils.reviewer_prompt import REVIEWER_PROMPT


class ReviewAgent(SpecialistAgent):
    name = "reviewer"

    def run(self, run_id: str, title: str, content: str) -> str:
        prompt = REVIEWER_PROMPT.format(title=title, content=content)

        def validate(text: str) -> str:
            if not text.strip():
                raise ValueError("Reviewer response is empty")
            if len(text) > 6_000:
                raise ValueError("Reviewer response exceeds safety limit")
            return text.strip()

        return self.complete(run_id, prompt, validate)
