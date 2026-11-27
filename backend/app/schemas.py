from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = Field(default=None, max_length=64)
    agent: str = "manager"

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str):
        value=value.strip()
        if not value:
            raise ValueError("Message cannot be blank.")
        return value

class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    project: str = Field(default="default", min_length=1, max_length=100)

    @field_validator("content", "project")
    @classmethod
    def trim_required_text(cls, value: str):
        value=value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value

class ResearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str):
        value=value.strip()
        if len(value)<2:
            raise ValueError("Search query is too short.")
        return value

class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    detail: str = Field(default="", max_length=10000)
    agent: str = "manager"

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str):
        value=value.strip()
        if not value:
            raise ValueError("Task title cannot be blank.")
        return value
