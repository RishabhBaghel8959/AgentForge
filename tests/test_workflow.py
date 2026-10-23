import json

from app.core import auth, tracing
from app.core.tracing import RunTracer, initialise_trace_store
from app.executor.executor import AgentExecutor
from app.models.workflow import GenerationResult


class FakeClient:
    model = "fake-model"

    def generate_with_metadata(self, prompt: str) -> GenerationResult:
        if "Autonomous Planning Agent" in prompt:
            text = json.dumps({
                "document_type": "Test Report",
                "goal": "Verify the workflow",
                "assumptions": [],
                "tasks": [{"id": 1, "title": "Summary", "description": "Write a summary"}],
            })
        elif "Senior Business Proposal Reviewer" in prompt:
            text = "Reviewed section."
        else:
            text = "Draft section."
        return GenerationResult(text=text, model=self.model, prompt_tokens=11, completion_tokens=7)


def test_orchestrator_records_a_validated_run(tmp_path, monkeypatch):
    database = tmp_path / "agentforge.db"
    monkeypatch.setattr(auth, "DATABASE_PATH", database)
    monkeypatch.setattr(tracing, "DATABASE_PATH", database)
    monkeypatch.setattr("app.executor.executor.DocxGenerator.generate", lambda *_: "output/Test_Report.docx")
    initialise_trace_store()

    result = AgentExecutor(client=FakeClient()).run("Create a report", user_id=42)
    trace = RunTracer().get(result["run_id"], user_id=42)

    assert result["status"] == "succeeded"
    assert result["generated_document"] == {"Summary": "Reviewed section."}
    assert trace["status"] == "succeeded"
    assert any(event["event_type"] == "validated" for event in trace["events"])
