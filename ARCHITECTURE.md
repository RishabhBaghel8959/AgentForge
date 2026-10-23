# AgentForge supervised graph

```text
Client/API
    -> Supervisor: classify request and enforce budgets
    -> Research Agent  ||  Planning Agent
    -> Execution Agent (bounded parallel section generation)
    -> Verification Agent (bounded parallel checks)
    -> Quality Gate: deliver | one repair round | stop
    -> Final result + persisted run trace
```

## Nodes and contracts

| Node | Input -> output | Permission | Termination condition |
| --- | --- | --- | --- |
| Supervisor | request -> admitted graph | Dispatch only; no model tools | Reject invalid input or dispatch accepted graph |
| Research | request -> `ResearchBrief` | Local model only; no retrieval tools | Valid JSON and no claimed external sources |
| Planning | request -> `ExecutionPlan` | Local model only | Valid typed JSON, 1-8 unique tasks |
| Execution | plan/task -> section | Local model only | Non-empty section below size limit |
| Verification | request/section -> `VerificationResult` | Local model only | Valid typed JSON with score and issues |
| Quality Gate | verification -> pass/repair/stop | Deterministic checks only | Score >= 70 and pass=true, or one repair budget exhausted |
| DOCX generator | validated sections -> `.docx` | Orchestrator-only filesystem write | File saved successfully |

## Safety and recovery

- Independent research and planning nodes run in controlled parallelism, capped at two workers.
- Section execution and verification are likewise capped at two concurrent workers.
- Every model request has a 5-second connection timeout and 120-second read timeout.
- Specialist retries are bounded to two attempts with 250 ms / 500 ms backoff.
- The Quality Gate allows only one repair round. Failed verification after repair stops the run; it does not silently deliver.
- Specialists have no shell, browser, filesystem, or external-network tool permissions. The Research Agent must return an empty source list because AgentForge has no retrieval connector.

## Trace model

SQLite stores a run record and append-only events. Events capture the graph node, model, attempt, token counts supplied by Ollama, declared tools, graph transition, timestamp, and failure details. The authenticated owner can retrieve a trace using `GET /runs/{run_id}`.
