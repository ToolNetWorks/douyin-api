from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ChannelVideosRequest(BaseModel):
    url: str = Field(..., description="Link kênh Douyin, ví dụ https://v.douyin.com/idFqvUms/ hoặc https://www.douyin.com/user/MS4wLjABAAAA...")
    max_count: int = Field(50, description="Số lượng video tối đa cần lấy (mặc định 50)", ge=1, le=500)
    cookie: Optional[str] = Field(None, description="Cookie Douyin tùy chọn nếu muốn phân trang sâu hơn")

class VideoItem(BaseModel):
    id: str
    url: str
    title: str
    play_url: Optional[str] = None
    cover_url: Optional[str] = None
    duration_seconds: float
    width: Optional[int] = None
    height: Optional[int] = None
    created_time: Optional[int] = None
    stats: Dict[str, int] = {}

class AuthorInfo(BaseModel):
    sec_uid: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    signature: Optional[str] = None
    total_works: Optional[str] = None

class ChannelVideosResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class VideoUrlsOnlyResponse(BaseModel):
    success: bool
    total: int
    sec_user_id: str
    video_urls: List[str]
