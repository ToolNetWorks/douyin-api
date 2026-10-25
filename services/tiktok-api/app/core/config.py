import os
from typing import Optional, Set
from pydantic import BaseModel

class Settings(BaseModel):
    PORT: int = int(os.environ.get("PORT", "10000"))
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    API_KEY: Optional[str] = os.environ.get("API_KEY", None)
    MAX_CONCURRENT_CRAWLS: int = int(os.environ.get("MAX_CONCURRENT_CRAWLS", "1"))
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    PAGE_SIZE: int = 15
    MAX_ALLOWED_COUNT: int = 500

    # Whitelisted TikTok hosts to prevent SSRF
    ALLOWED_HOSTS: Set[str] = {
        "tiktok.com",
        "www.tiktok.com",
        "vt.tiktok.com",
        "vm.tiktok.com",
        "m.tiktok.com",
        "iesdouyin.com",
    }

settings = Settings()
