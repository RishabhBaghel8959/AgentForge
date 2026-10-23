from pydantic import BaseModel, Field

class AgentRequest(BaseModel):
    request: str


class Credentials(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=128)
