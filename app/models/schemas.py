from pydantic import BaseModel

class AgentRequest(BaseModel):
    request: str