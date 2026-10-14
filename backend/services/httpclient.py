import httpx
from app.config import get_settings


def make_client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.request_timeout_seconds),
        headers={"User-Agent": "MedicalResearchChatbot/0.1 (research prototype)"},
        follow_redirects=True,
    )
