"""Supervisor-led graph orchestration with bounded parallel execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from app.agents.base import AgentExecutionError
from app.agents.planner import PlanningAgent
from app.agents.quality_gate import QualityGate
from app.agents.research import ResearchAgent
from app.agents.supervisor import Supervisor
from app.agents.verification import VerificationAgent
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
    """Graph: supervisor -> (research || plan) -> execution -> verification -> quality gate."""

    def __init__(self, client: OllamaClient | None = None, tracer: RunTracer | None = None):
        self.client = client or OllamaClient()
        self.tracer = tracer or RunTracer()
        self.supervisor = Supervisor(self.tracer)
        self.researcher = ResearchAgent(self.client, self.tracer)
        self.planner = PlanningAgent(self.client, self.tracer)
        self.writer = WritingAgent(self.client, self.tracer)
        self.verifier = VerificationAgent(self.client, self.tracer)
        self.quality_gate = QualityGate()

    def _parallel(self, tasks: dict[str, tuple], worker_limit: int) -> dict:
        """Execute independent nodes while preserving state ownership in the orchestrator."""
        results = {}
        with ThreadPoolExecutor(max_workers=worker_limit) as pool:
            futures = {pool.submit(function, *args): name for name, (function, args) in tasks.items()}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        return results

    def run(self, request: str, user_id: int) -> dict:
        run_id = str(uuid4())
        state = WorkflowState(run_id=run_id, user_id=user_id, request=request)
        self.tracer.start(run_id, user_id, request)
        try:
            self.supervisor.admit(run_id, request)
            self.tracer.event(run_id, "supervisor", "dispatch_parallel", details={"nodes": ["researcher", "planner"]})
            preparation = self._parallel({
                "research": (self.researcher.run, (run_id, request)),
                "plan": (self.planner.run, (run_id, request)),
            }, self.supervisor.max_parallel_workers)
            state.research, state.plan = preparation["research"], preparation["plan"]

            self.tracer.event(run_id, "supervisor", "handoff", details={"from": ["researcher", "planner"], "to": "executor"})
            drafts = self._parallel({
                task.title: (self.writer.run, (run_id, state.plan, task)) for task in state.plan.tasks
            }, self.supervisor.max_parallel_workers)
            state.draft_sections = {task.title: drafts[task.title] for task in state.plan.tasks}
            for task in state.plan.tasks:
                task.status = "Completed"

            self.tracer.event(run_id, "supervisor", "handoff", details={"from": "executor", "to": "verifier"})
            verified = self._parallel({
                title: (self.verifier.run, (run_id, request, title, content))
                for title, content in state.draft_sections.items()
            }, self.supervisor.max_parallel_workers)
            state.reviewed_sections = dict(state.draft_sections)
            state.verification = verified

            passed, repairs = self.quality_gate.evaluate(verified)
            self.tracer.event(run_id, "quality_gate", "evaluated", details={
                "passed": passed,
                "repair_sections": list(repairs),
                "verification_details": {
                    title: {"passed": result.passed, "quality_score": result.quality_score, "issues": result.issues}
                    for title, result in verified.items()
                },
            })
            if not passed:
                self.tracer.event(run_id, "quality_gate", "repair_round", attempt=1, details={"sections": list(repairs)})
                repaired = self._parallel({
                    title: (self.writer.repair, (run_id, title, state.reviewed_sections[title], issues))
                    for title, issues in repairs.items()
                }, self.supervisor.max_parallel_workers)
                state.reviewed_sections.update(repaired)
                state.verification.update(self._parallel({
                    title: (self.verifier.run, (run_id, request, title, content))
                    for title, content in repaired.items()
                }, self.supervisor.max_parallel_workers))
                passed, remaining = self.quality_gate.evaluate(state.verification)
                self.tracer.event(run_id, "quality_gate", "re_evaluated", details={
                    "passed": passed,
                    "remaining": list(remaining),
                    "verification_details": {
                        title: {"passed": result.passed, "quality_score": result.quality_score, "issues": result.issues}
                        for title, result in state.verification.items()
                    },
                })
                if not passed:
                    raise ValueError("Quality gate rejected the run after the allowed repair round.")

            state.document_path = DocxGenerator.generate(state.plan.document_type, state.reviewed_sections)
            state.status = RunStatus.SUCCEEDED
            self.tracer.finish(run_id, state.document_path)
            self.tracer.event(run_id, "supervisor", "delivered", tools=[], details={"sections": len(state.reviewed_sections)})
            return {"status": state.status, "run_id": state.run_id, "request": state.request,
                    "execution_plan": state.plan.model_dump(), "generated_document": state.reviewed_sections,
                    "document_path": state.document_path}
        except (AgentExecutionError, ValueError, OSError) as error:
            state.status = RunStatus.FAILED
            self.tracer.fail(run_id, str(error))
            self.tracer.event(run_id, "supervisor", "stopped", details={"error": str(error)[:500]})
            raise RunFailed(run_id, "The document run failed. Inspect its trace for details.") from error
