from app.planner.planner import Planner
from app.llm.ollama_client import OllamaClient
from app.utils.executor_prompt import EXECUTOR_PROMPT
from app.document.docx_generator import DocxGenerator
from app.reviewer.reviewer import Reviewer


class AgentExecutor:

    def __init__(self):

        self.planner = Planner()

        self.client = OllamaClient()

        self.reviewer = Reviewer()


    def run(self, request):

        # Step 1
        plan = self.planner.create_plan(request)

        # Step 2
        generated_document = {}

        # Step 3
        for task in plan["tasks"]:

            prompt = EXECUTOR_PROMPT.format(
                document_type=plan["document_type"],
                goal=plan["goal"],
                assumptions="\n".join(plan["assumptions"]),
                title=task["title"],
                description=task["description"]
            )

            print(f"Executing : {task['title']}")

            response = self.client.generate(prompt)

            generated_document[task["title"]] = response

            task["status"] = "Completed"


        # Step 4 
        generated_document = self.reviewer.review(generated_document)


        # Step 5
        document_path = DocxGenerator.generate(
            plan["document_type"],
            generated_document
        )
        
        # Step 6

        return {

            "status": "success",
            "request": request,
            "execution_plan": plan,
            "generated_document": generated_document,
            "document_path": document_path
        }