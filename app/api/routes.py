from fastapi import APIRouter
from app.models.schemas import AgentRequest
from app.executor.executor import AgentExecutor

router = APIRouter()

executor = AgentExecutor()

@router.post("/agent")
def run_agent(request: AgentRequest):

    return executor.run(request.request)