import json
import re


class JSONParser:

    @staticmethod
    def extract_json(text: str):

        text = text.strip()

        # remove markdown

        text = text.replace("```json", "")

        text = text.replace("```", "")

        match = re.search(r"\{.*\}", text, re.DOTALL)

        if not match:

            raise ValueError("No JSON Found")

        return json.loads(match.group())