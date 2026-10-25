from typing import List, Optional
from pydantic import BaseModel, Field

class TikTokChannelRequest(BaseModel):
    url: str = Field(
        ...,
        description="Link tài khoản TikTok (ví dụ: https://www.tiktok.com/@username, @username, link rút gọn vt.tiktok.com hoặc link video)",
    )
    max_count: int = Field(
        30,
        ge=1,
        le=500,
        description="Số lượng video tối đa cần cào (mặc định: 30, tối đa: 500)",
    )

class TikTokVideoItem(BaseModel):
    video_id: str = Field(..., description="ID video TikTok")
    url: str = Field(..., description="URL xem video trên TikTok")
    title: Optional[str] = Field(None, description="Tiêu đề hoặc mô tả bài đăng")
    cover_url: Optional[str] = Field(None, description="Ảnh bìa video")
    duration_seconds: Optional[int] = Field(None, description="Thời lượng video tính bằng giây")
    created_at: Optional[int] = Field(None, description="Thời điểm đăng (UNIX timestamp)")
    likes: Optional[int] = Field(None, description="Lượt thích (diggCount)")
    comments: Optional[int] = Field(None, description="Lượt bình luận (commentCount)")
    shares: Optional[int] = Field(None, description="Lượt chia sẻ (shareCount)")
    views: Optional[int] = Field(None, description="Lượt xem (playCount)")
    bookmarks: Optional[int] = Field(None, description="Lượt lưu/yêu thích (collectCount)")

class TikTokAuthorInfo(BaseModel):
    nickname: Optional[str] = Field(None, description="Tên hiển thị")
    unique_id: Optional[str] = Field(None, description="TikTok Username (@unique_id)")
    sec_uid: Optional[str] = Field(None, description="Mã bảo mật định danh tác giả (secUid)")
    avatar: Optional[str] = Field(None, description="URL ảnh đại diện tác giả")
    signature: Optional[str] = Field(None, description="Tiểu sử / Bio")
    follower_count: Optional[int] = Field(None, description="Số người theo dõi")
    following_count: Optional[int] = Field(None, description="Số người đang theo dõi")
    heart_count: Optional[int] = Field(None, description="Tổng số lượt thích")
    video_count: Optional[int] = Field(None, description="Tổng số video của kênh")

class TikTokChannelResponse(BaseModel):
    success: bool
    platform: str = "tiktok"
    username: Optional[str] = None
    author: Optional[TikTokAuthorInfo] = None
    total_collected: int = 0
    video_urls: List[str] = []
    videos: List[TikTokVideoItem] = []
    has_more: bool = False
    next_cursor: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None

class TikTokVideoUrlsResponse(BaseModel):
    success: bool
    platform: str = "tiktok"
    username: Optional[str] = None
    total_collected: int = 0
    video_urls: List[str] = []
    has_more: bool = False
    next_cursor: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None

class TikTokVideoInfoResponse(BaseModel):
    success: bool
    platform: str = "tiktok"
    video: Optional[TikTokVideoItem] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
