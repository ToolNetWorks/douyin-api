import os
from pathlib import Path
from typing import Optional, List

class Settings:
    PROJECT_NAME: str = "Douyin Channel Video Scraper API"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = (
        "REST API tự host để lấy toàn bộ URL video của một kênh Douyin từ link kênh "
        "(hỗ trợ cả link rút gọn v.douyin.com, link chia sẻ, link web). Không phụ thuộc bên thứ 3."
    )

    # Base directory paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    ROOT_DIR: Path = BASE_DIR.parent.parent if (BASE_DIR.parent.name == "services") else BASE_DIR

    # Server configuration
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8088"))
    API_KEY: str = os.environ.get("API_KEY", "").strip()

    # Browser & Chromium configuration
    CHROME_PATH: Optional[str] = os.environ.get("CHROME_PATH")
    MAX_CONCURRENT_CRAWLS: int = int(os.environ.get("MAX_CONCURRENT_CRAWLS", "1"))
    PAGE_TIMEOUT_MS: int = int(os.environ.get("PAGE_TIMEOUT_MS", "45000"))

    # Cookie settings
    COOKIE_STR: str = os.environ.get("DOUYIN_COOKIE", "").strip()

    @property
    def cookie_search_paths(self) -> List[Path]:
        return [
            self.BASE_DIR / "cookie.txt",
            self.ROOT_DIR / "cookie.txt",
            self.BASE_DIR / "cookies.json",
            self.ROOT_DIR / "cookies.json",
            self.BASE_DIR / ".env",
            self.ROOT_DIR / ".env",
            Path("/root/douyin/cookie.txt"),
            Path("/root/douyin/cookies.json"),
            Path("/app/cookie.txt"),
            Path("/app/cookies.json"),
        ]

settings = Settings()
