"""Shared retry and trace policy for specialist agents."""

import time
from collections.abc import Callable
from typing import TypeVar

from app.core.tracing import RunTracer
from app.models.workflow import GenerationResult

T = TypeVar("T")


class AgentExecutionError(RuntimeError):
    pass


class SpecialistAgent:
    name = "specialist"
    max_attempts = 2

    def __init__(self, client, tracer: RunTracer):
        self.client = client
        self.tracer = tracer

    def complete(self, run_id: str, prompt: str, validator: Callable[[str], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self.tracer.event(run_id, self.name, "started", model=self.client.model, attempt=attempt, tools=[])
            try:
                result: GenerationResult = self.client.generate_with_metadata(prompt)
                value = validator(result.text)
                self.tracer.event(
                    run_id, self.name, "validated", model=result.model, attempt=attempt,
                    prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens, tools=[],
                )
                return value
            except Exception as error:
                last_error = error
                self.tracer.event(run_id, self.name, "failed_attempt", model=self.client.model, attempt=attempt,
                                  tools=[], details={"error": str(error)[:500]})
                if attempt < self.max_attempts:
                    time.sleep(0.25 * attempt)
        raise AgentExecutionError(f"{self.name} failed after {self.max_attempts} attempts: {last_error}")
