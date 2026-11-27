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


class SkillCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2, max_length=240)
    instructions: str = Field(min_length=10, max_length=5000)
    triggers: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("name", "description", "instructions")
    @classmethod
    def trim_skill_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Skill fields cannot be blank.")
        return value

    @field_validator("triggers")
    @classmethod
    def normalize_triggers(cls, values: list[str]):
        cleaned = []
        for value in values:
            item = value.strip().lower()
            if item and item not in cleaned:
                cleaned.append(item[:50])
        return cleaned

class SkillUpdate(BaseModel):
    enabled: bool
