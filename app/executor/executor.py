"""The orchestrator is the sole owner of workflow state and handoffs."""

from uuid import uuid4

from app.agents.base import AgentExecutionError
from app.agents.planner import PlanningAgent
from app.agents.reviewer import ReviewAgent
from app.agents.writer import WritingAgent
from app.core.tracing import RunTracer
from app.document.docx_generator import DocxGenerator
from app.llm.ollama_client import OllamaClient
from app.models.workflow import RunStatus, WorkflowState


class RunFailed(RuntimeError):
    def __init__(self, run_id: str, message: str):
        super().__init__(message)
        self.run_id = run_id


class AgentExecutor:
    """Coordinates typed specialist handoffs; specialists cannot call each other."""

    def __init__(self, client: OllamaClient | None = None, tracer: RunTracer | None = None):
        self.client = client or OllamaClient()
        self.tracer = tracer or RunTracer()
        self.planner = PlanningAgent(self.client, self.tracer)
        self.writer = WritingAgent(self.client, self.tracer)
        self.reviewer = ReviewAgent(self.client, self.tracer)

    def run(self, request: str, user_id: int) -> dict:
        run_id = str(uuid4())
        state = WorkflowState(run_id=run_id, user_id=user_id, request=request)
        self.tracer.start(run_id, user_id, request)
        try:
            state.plan = self.planner.run(run_id, request)
            self.tracer.event(run_id, "orchestrator", "handoff", details={"from": "planner", "to": "writer"})
            for task in state.plan.tasks:
                state.draft_sections[task.title] = self.writer.run(run_id, state.plan, task)
                task.status = "Completed"
            self.tracer.event(run_id, "orchestrator", "handoff", details={"from": "writer", "to": "reviewer"})
            for title, content in state.draft_sections.items():
                state.reviewed_sections[title] = self.reviewer.run(run_id, title, content)
            state.document_path = DocxGenerator.generate(state.plan.document_type, state.reviewed_sections)
            state.status = RunStatus.SUCCEEDED
            self.tracer.finish(run_id, state.document_path)
            self.tracer.event(run_id, "orchestrator", "validated_output", tools=[], details={"sections": len(state.reviewed_sections)})
            return {"status": state.status, "run_id": state.run_id, "request": state.request,
                    "execution_plan": state.plan.model_dump(), "generated_document": state.reviewed_sections,
                    "document_path": state.document_path}
        except (AgentExecutionError, ValueError, OSError) as error:
            state.status = RunStatus.FAILED
            state.error = str(error)
            self.tracer.fail(run_id, state.error)
            raise RunFailed(run_id, "The document run failed. Inspect its trace for details.") from error
