from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = None
    agent: str = "manager"

class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    project: str = "default"

class ResearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)

class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    detail: str = ""
