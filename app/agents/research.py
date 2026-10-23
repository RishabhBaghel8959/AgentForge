import json

from app.agents.base import SpecialistAgent
from app.models.workflow import ResearchBrief


RESEARCH_PROMPT = """
You are the Research Agent in a local document workflow.
Extract only useful context and explicitly state evidence limitations for this request.
You have NO web, filesystem, or external tools. Do not invent sources, statistics, citations, or facts.
Return only JSON: {{"context":["..."],"sources":[],"limitations":["..."]}}.

Request: {request}
"""


class ResearchAgent(SpecialistAgent):
    name = "researcher"

    def run(self, run_id: str, request: str) -> ResearchBrief:
        def validate(text: str) -> ResearchBrief:
            cleaned = text.replace("```json", "").replace("```", "").strip()
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("Research response contains no JSON object")
            brief = ResearchBrief.model_validate(json.loads(cleaned[start:end + 1]))
            if brief.sources:
                raise ValueError("Research agent cannot claim sources without retrieval tools")
            return brief

        return self.complete(run_id, RESEARCH_PROMPT.format(request=request), validate)
