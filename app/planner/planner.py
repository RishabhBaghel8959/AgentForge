import json

from app.llm.ollama_client import OllamaClient
from app.utils.prompts import PLANNER_PROMPT
from app.utils.json_parser import JSONParser
from app.utils.logger import info
from app.core.logger import logger


class Planner:

    def __init__(self):

        self.client = OllamaClient()

    def create_plan(self, request):

        logger.info("Planning started...")

        prompt = PLANNER_PROMPT.format(
            request=request
        )

        try:
            response = self.client.generate(prompt)
        except Exception as e:
            response = f"Generation Failed: {e}"
        return JSONParser.extract_json(response)