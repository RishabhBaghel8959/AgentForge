from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.models.schemas import AgentRequest
from app.executor.executor import AgentExecutor

router = APIRouter()

executor = AgentExecutor()

@router.post("/agent")
def run_agent(request: AgentRequest):

    return executor.run(request.request)


@router.get("/documents/{filename}")
def download_document(filename: str):
    """Serve only documents created by this application."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid document name")

    document = Path("output") / filename
    if not document.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    return FileResponse(
        document,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
