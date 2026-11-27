from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    database_path: str = str(ROOT / "data" / "agent_studio.sqlite3")
    workspace_path: str = str(ROOT / "data" / "workspace")
    frontend_origin: str = "http://localhost:3000"
    request_timeout_seconds: int = 120
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
