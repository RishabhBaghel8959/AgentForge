# AgentForge execution architecture

`AgentExecutor` is the orchestrator and owns the only mutable `WorkflowState`. Specialist agents do not call each other and cannot write files or execute tools.

```text
request → orchestrator → planner → writer (once per validated task) → reviewer → DOCX generator
                         │                 │                              │
                         └────────── RunTracer records every handoff ──────┘
```

| Component | Typed input → output | Permission | Completion rule |
| --- | --- | --- | --- |
| Planner | `str` → `ExecutionPlan` | Model completion only | Valid JSON matches `ExecutionPlan` |
| Writer | `ExecutionPlan`, `Task` → `str` | Model completion only | Non-empty section within size limit |
| Reviewer | title, section → `str` | Model completion only | Non-empty reviewed section within size limit |
| Orchestrator | request, user ID → result | Calls agents; creates DOCX | All stages validate and DOCX saves |
| RunTracer | events → SQLite rows | Append-only tracing | Event persisted |

## Safety policy

- Each model call has a 5-second connection and 120-second read timeout.
- Each specialist has at most two attempts, with a bounded 250 ms / 500 ms backoff.
- Planner output is parsed and validated against a typed schema before writing begins.
- Writer/reviewer outputs must be non-empty and remain under a 6,000-character bound.
- No shell, browser, filesystem, or network tools are exposed to specialists. The orchestrator alone writes the final DOCX.
- A failed retry budget yields an explicit `failed` run; it never becomes a success based on an agent's self-report.

## Tracing

Runs and events are persisted to the local SQLite database. Each event includes agent name, event type, model, attempt, token counts returned by Ollama, declared tools, details, and timestamp.

Authenticated users can retrieve their own trace with `GET /runs/{run_id}`. Failed `POST /agent` responses include the `run_id` for inspection.
