from app.core.tracing import RunTracer


class Supervisor:
    """Classifies the task and enforces execution budgets before a graph starts."""

    max_request_chars = 1_500
    max_parallel_workers = 2
    max_repair_rounds = 1

    def __init__(self, tracer: RunTracer):
        self.tracer = tracer

    def admit(self, run_id: str, request: str) -> None:
        if not request or len(request.strip()) < 8:
            raise ValueError("Please provide a more detailed document request.")
        if len(request) > self.max_request_chars:
            raise ValueError(f"Requests are limited to {self.max_request_chars} characters.")
        self.tracer.event(run_id, "supervisor", "admitted", tools=[], details={
            "classification": "document_generation",
            "parallel_worker_limit": self.max_parallel_workers,
            "repair_limit": self.max_repair_rounds,
        })
