from app.llm.ollama_client import OllamaClient
from app.utils.reviewer_prompt import REVIEWER_PROMPT


class Reviewer:

    def __init__(self):

        self.client = OllamaClient()

    def review(self, document):

        improved_document = {}

        for title, content in document.items():

            prompt = REVIEWER_PROMPT.format(

                title=title,

                content=content

            )

            print(f"Reviewing : {title}")

            response = self.client.generate(prompt)

            improved_document[title] = response

        return improved_document