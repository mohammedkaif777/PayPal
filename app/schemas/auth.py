from pydantic import BaseModel


class ActorResponse(BaseModel):
    id: int
    name: str
    role: str
