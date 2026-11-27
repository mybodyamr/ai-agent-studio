import httpx
from .config import settings

async def generate(messages: list[dict], system: str | None = None) -> str:
    msgs = ([{"role":"system","content":system}] if system else []) + messages
    payload = {"model": settings.ollama_model, "messages": msgs, "stream": False}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()

async def status():
    async with httpx.AsyncClient(timeout=4) as client:
        try:
            r = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
            return {"connected": True, "model": settings.ollama_model, "available_models": models,
                    "model_available": any(settings.ollama_model == m or settings.ollama_model + ":latest" == m for m in models)}
        except Exception:
            return {"connected": False, "model": settings.ollama_model, "available_models": [], "model_available": False}
