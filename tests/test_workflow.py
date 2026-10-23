import json

from app.core import auth, tracing
from app.core.tracing import RunTracer, initialise_trace_store
from app.executor.executor import AgentExecutor
from app.models.workflow import GenerationResult


class FakeClient:
    model = "fake-model"

    def generate_with_metadata(self, prompt: str) -> GenerationResult:
        if "Research Agent" in prompt:
            text = json.dumps({"context": ["Local test context"], "sources": [], "limitations": ["No external retrieval"]})
        elif "Autonomous Planning Agent" in prompt:
            text = json.dumps({
                "document_type": "Test Report",
                "goal": "Verify the workflow",
                "assumptions": [],
                "tasks": [{"id": 1, "title": "Summary", "description": "Write a summary"}],
            })
        elif "Verification Agent" in prompt:
            text = json.dumps({"passed": True, "issues": [], "quality_score": 90})
        else:
            text = "Draft section."
        return GenerationResult(text=text, model=self.model, prompt_tokens=11, completion_tokens=7)


class RepairThenSuccessClient:
    """Simulates: first verification fails -> repair succeeds -> second verification passes."""

    model = "fake-model"

    def __init__(self):
        self.research_calls = 0

    def generate_with_metadata(self, prompt: str) -> GenerationResult:
        if "Research Agent" in prompt:
            text = json.dumps({"context": ["Local test context"], "sources": [], "limitations": ["No external retrieval"]})
        elif "Autonomous Planning Agent" in prompt:
            text = json.dumps({
                "document_type": "Test Report",
                "goal": "Verify the workflow",
                "assumptions": [],
                "tasks": [{"id": 1, "title": "Summary", "description": "Write a summary"}],
            })
        elif "Verification Agent" in prompt:
            self.research_calls += 1
            if self.research_calls == 1:
                # First verification fails, triggers repair
                text = json.dumps({"passed": False, "issues": ["Missing required content"], "quality_score": 60})
            else:
                # Final verification passes after repair
                text = json.dumps({"passed": True, "issues": [], "quality_score": 95})
        else:
            text = "Repaired section content."
        return GenerationResult(text=text, model=self.model, prompt_tokens=11, completion_tokens=7)


class PersistentFailedVerificationClient:
    """Always fails verification after repair — tests the failure path."""

    model = "fake-model"

    def generate_with_metadata(self, prompt: str) -> GenerationResult:
        if "Research Agent" in prompt:
            text = json.dumps({"context": ["Local test context"], "sources": [], "limitations": ["No external retrieval"]})
        elif "Autonomous Planning Agent" in prompt:
            text = json.dumps({
                "document_type": "Test Report",
                "goal": "Verify the workflow",
                "assumptions": [],
                "tasks": [{"id": 1, "title": "Summary", "description": "Write a summary"}],
            })
        elif "Verification Agent" in prompt:
            text = json.dumps({"passed": False, "issues": ["Still missing required content"], "quality_score": 50})
        else:
            text = "Repaired section content."
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
    assert result["generated_document"] == {"Summary": "Draft section."}
    assert trace["status"] == "succeeded"
    assert any(event["event_type"] == "validated" for event in trace["events"])


def test_orchestrator_repairs_then_succeeds(tmp_path, monkeypatch):
    database = tmp_path / "agentforge.db"
    monkeypatch.setattr(auth, "DATABASE_PATH", database)
    monkeypatch.setattr(tracing, "DATABASE_PATH", database)
    monkeypatch.setattr("app.executor.executor.DocxGenerator.generate", lambda *_: "output/Test_Report.docx")
    initialise_trace_store()

    result = AgentExecutor(client=RepairThenSuccessClient()).run("Create a report", user_id=42)
    trace = RunTracer().get(result["run_id"], user_id=42)

    assert result["status"] == "succeeded"
    assert result["generated_document"] == {"Summary": "Repaired section content."}
    assert trace["status"] == "succeeded"
    event_types = [event["event_type"] for event in trace["events"]]
    assert "repair_round" in event_types
    assert "re_evaluated" in event_types


def test_orchestrator_rejected_after_repair(tmp_path, monkeypatch):
    database = tmp_path / "agentforge.db"
    monkeypatch.setattr(auth, "DATABASE_PATH", database)
    monkeypatch.setattr(tracing, "DATABASE_PATH", database)
    monkeypatch.setattr("app.executor.executor.DocxGenerator.generate", lambda *_: "output/Test_Report.docx")
    initialise_trace_store()

    from app.executor.executor import RunFailed

    try:
        AgentExecutor(client=PersistentFailedVerificationClient()).run("Create a report", user_id=42)
        assert False, "Expected RunFailed to be raised"
    except RunFailed as error:
        assert error.run_id
        trace = RunTracer().get(error.run_id, user_id=42)
        assert trace["status"] == "failed"
