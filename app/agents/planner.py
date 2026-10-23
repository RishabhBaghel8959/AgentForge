import json

from app.agents.base import SpecialistAgent
from app.models.workflow import ExecutionPlan
from app.utils.prompts import PLANNER_PROMPT


class PlanningAgent(SpecialistAgent):
    name = "planner"

    def run(self, run_id: str, request: str) -> ExecutionPlan:
        def validate(text: str) -> ExecutionPlan:
            cleaned = text.replace("```json", "").replace("```", "").strip()
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("Planner response contains no JSON object")
            return ExecutionPlan.model_validate(json.loads(cleaned[start:end + 1]))

        return self.complete(run_id, PLANNER_PROMPT.format(request=request), validate)
