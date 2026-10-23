from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from app.api.dependencies import current_user
from app.core.auth import create_access_token, create_user, find_user, verify_password
from app.models.schemas import AgentRequest, Credentials
from app.executor.executor import AgentExecutor
from app.executor.executor import RunFailed
from app.core.tracing import RunTracer

router = APIRouter()

executor = AgentExecutor()

@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(credentials: Credentials):
    user = create_user(str(credentials.email), credentials.password)
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user}


@router.post("/auth/login")
def login(credentials: Credentials):
    user = find_user(str(credentials.email))
    if user is None or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    public_user = {"id": user["id"], "email": user["email"]}
    return {"access_token": create_access_token(public_user), "token_type": "bearer", "user": public_user}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return {"id": int(user["sub"]), "email": user["email"]}

@router.post("/agent")
def run_agent(request: AgentRequest, user: dict = Depends(current_user)):
    try:
        return executor.run(request.request, int(user["sub"]))
    except RunFailed as error:
        raise HTTPException(status_code=502, detail={"message": str(error), "run_id": error.run_id}) from error


@router.get("/runs/{run_id}")
def get_run(run_id: str, user: dict = Depends(current_user)):
    trace = RunTracer().get(run_id, int(user["sub"]))
    if trace is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return trace


@router.get("/documents/{filename}")
def download_document(filename: str, _user: dict = Depends(current_user)):
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
