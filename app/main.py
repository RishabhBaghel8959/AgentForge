from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.auth import initialise_database
from app.core.cache import AgentResultCache
from app.core.tracing import initialise_trace_store

app = FastAPI(
    title="Autonomous AI Agent",
    version="1.0.0",
)

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    initialise_database()
    initialise_trace_store()
    AgentResultCache().healthcheck()

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")
