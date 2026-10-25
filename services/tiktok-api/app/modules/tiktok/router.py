import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Request, Depends, Header

from app.core.config import settings
from app.modules.tiktok.schemas import (
    TikTokChannelRequest,
    TikTokChannelResponse,
    TikTokVideoUrlsResponse,
    TikTokVideoInfoResponse,
)
from app.modules.tiktok.scraper import TikTokScraper

logger = logging.getLogger("tiktok_router")

router = APIRouter(prefix="/api/tiktok")
scraper = TikTokScraper()

def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None),
):
    """
    Xác thực API Key:
    - Bắt buộc server phải có cấu hình API_KEY qua biến môi trường.
    - Nếu server chưa cấu hình API_KEY, từ chối mọi yêu cầu crawl (500).
    - Hỗ trợ truyền qua Header 'X-API-Key' hoặc 'Authorization: Bearer <key>' hoặc Query '?api_key=...'.
    """
    configured_key = (settings.API_KEY or "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=500,
            detail="Lỗi cấu hình server: Biến môi trường API_KEY chưa được thiết lập trên server. Vui lòng cấu hình API_KEY trước khi crawl.",
        )

    token = x_api_key or api_key
    if not token and "authorization" in request.headers:
        auth = request.headers["authorization"]
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()

    if not token or token != configured_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: API Key không hợp lệ hoặc bị thiếu. Vui lòng truyền qua Header 'X-API-Key' hoặc 'Authorization: Bearer <token>'.",
        )
    return True

@router.post(
    "/channel/videos",
    response_model=TikTokChannelResponse,
    summary="Cào danh sách video kèm metadata đầy đủ (POST)",
    dependencies=[Depends(verify_api_key)],
)
async def post_channel_videos(body: TikTokChannelRequest):
    """
    POST endpoint: Nhận URL tài khoản TikTok và số lượng video cần lấy,
    trả về danh sách video công khai kèm metadata đầy đủ (stats, duration, cover, title).
    """
    result = await scraper.get_channel_videos(
        input_url=body.url,
        max_count=body.max_count,
    )
    return result

@router.get(
    "/channel/videos",
    response_model=TikTokChannelResponse,
    summary="Cào danh sách video kèm metadata đầy đủ (GET)",
    dependencies=[Depends(verify_api_key)],
)
async def get_channel_videos(
    url: str = Query(..., description="Link tài khoản TikTok (ví dụ: https://www.tiktok.com/@username, vt.tiktok.com)"),
    max_count: int = Query(30, ge=1, le=500, description="Số lượng video tối đa"),
):
    """
    GET endpoint tương ứng để lấy danh sách video kèm metadata đầy đủ.
    """
    result = await scraper.get_channel_videos(
        input_url=url,
        max_count=max_count,
    )
    return result

@router.post(
    "/video/urls",
    response_model=TikTokVideoUrlsResponse,
    summary="Chỉ lấy danh sách URL video (POST)",
    dependencies=[Depends(verify_api_key)],
)
async def post_video_urls(body: TikTokChannelRequest):
    """
    POST endpoint tối giản: Chỉ trả về danh sách URL video TikTok.
    """
    result = await scraper.get_channel_videos(
        input_url=body.url,
        max_count=body.max_count,
    )
    return {
        "success": result.get("success", False),
        "platform": "tiktok",
        "username": result.get("username"),
        "total_collected": result.get("total_collected", 0),
        "video_urls": result.get("video_urls", []),
        "has_more": result.get("has_more", False),
        "next_cursor": result.get("next_cursor"),
        "error_code": result.get("error_code"),
        "message": result.get("message"),
    }

@router.get(
    "/video/urls",
    response_model=TikTokVideoUrlsResponse,
    summary="Chỉ lấy danh sách URL video (GET)",
    dependencies=[Depends(verify_api_key)],
)
async def get_video_urls(
    url: str = Query(..., description="Link tài khoản TikTok"),
    max_count: int = Query(30, ge=1, le=500, description="Số lượng video tối đa"),
):
    """
    GET endpoint tối giản: Chỉ trả về danh sách URL video TikTok.
    """
    result = await scraper.get_channel_videos(
        input_url=url,
        max_count=max_count,
    )
    return {
        "success": result.get("success", False),
        "platform": "tiktok",
        "username": result.get("username"),
        "total_collected": result.get("total_collected", 0),
        "video_urls": result.get("video_urls", []),
        "has_more": result.get("has_more", False),
        "next_cursor": result.get("next_cursor"),
        "error_code": result.get("error_code"),
        "message": result.get("message"),
    }

@router.get(
    "/video/info",
    response_model=TikTokVideoInfoResponse,
    summary="Lấy metadata chi tiết của một video đơn lẻ",
    dependencies=[Depends(verify_api_key)],
)
async def get_single_video(
    url: str = Query(..., description="URL video TikTok (ví dụ: https://www.tiktok.com/@user/video/123456789)"),
):
    """
    Trích xuất metadata đầy đủ của 1 video TikTok từ URL.
    """
    result = await scraper.get_single_video_info(video_url=url)
    return result
