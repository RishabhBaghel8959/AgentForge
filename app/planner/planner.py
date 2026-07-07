import json

from app.llm.ollama_client import OllamaClient
from app.utils.prompts import PLANNER_PROMPT


class Planner:

    def __init__(self):
        self.llm = OllamaClient()

    def create_plan(self, request: str):

        prompt = PLANNER_PROMPT.format(request=request)

        response = self.llm.generate(prompt)

        try:
            return json.loads(response)

        except Exception:

            return {
                "tasks": [
                    {
                        "id": 1,
                        "task": "Unable to Parse LLM Response",
                        "priority": "High",
                        "status": "Failed"
                    }
                ],
                "raw_response": response
            }