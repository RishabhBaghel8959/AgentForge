from app.agents.base import SpecialistAgent
from app.models.workflow import ExecutionPlan, Task
from app.utils.executor_prompt import EXECUTOR_PROMPT


class WritingAgent(SpecialistAgent):
    name = "writer"

    def run(self, run_id: str, plan: ExecutionPlan, task: Task) -> str:
        prompt = EXECUTOR_PROMPT.format(
            document_type=plan.document_type,
            goal=plan.goal,
            assumptions="\n".join(plan.assumptions),
            title=task.title,
            description=task.description,
        )

        def validate(text: str) -> str:
            if not text.strip():
                raise ValueError("Writer response is empty")
            if len(text) > 6_000:
                raise ValueError("Writer response exceeds safety limit")
            return text.strip()

        return self.complete(run_id, prompt, validate)

    def repair(self, run_id: str, title: str, content: str, issues: list[str]) -> str:
        prompt = f"""You are the Execution Agent repairing one document section.
Section title: {title}
Current content: {content}
Verification issues: {'; '.join(issues)}
Return only a corrected section in plain text. Do not mention the review process."""

        def validate(text: str) -> str:
            if not text.strip() or len(text) > 6_000:
                raise ValueError("Repair output is invalid")
            return text.strip()

        return self.complete(run_id, prompt, validate)
