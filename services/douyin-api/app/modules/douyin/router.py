import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Request, Depends, Header

from app.core.config import settings
from app.modules.douyin.schemas import (
    ChannelVideosRequest,
    ChannelVideosResponse,
    VideoUrlsOnlyResponse,
)
from app.modules.douyin.scraper import DouyinScraper

logger = logging.getLogger("douyin_router")

router = APIRouter(prefix="/api/douyin")
scraper = DouyinScraper()

def check_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None),
):
    """
    Xác thực API Key nếu máy chủ có cài đặt biến môi trường API_KEY.
    Nếu server không cài API_KEY thì bỏ qua (cho phép truy cập tự do).
    """
    if not settings.API_KEY:
        return True
    
    token = x_api_key or api_key
    if not token and "authorization" in request.headers:
        auth = request.headers["authorization"]
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            
    if token != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: API Key không hợp lệ. Vui lòng truyền qua Header 'X-API-Key' hoặc Query '?api_key=...'"
        )
    return True

@router.post(
    "/channel/videos",
    response_model=ChannelVideosResponse,
    tags=["Channel Full Details"],
    summary="Lấy toàn bộ video + link MP4 tải trực tiếp + metadata (POST)",
    dependencies=[Depends(check_api_key)]
)
async def get_channel_videos_post(payload: ChannelVideosRequest):
    """
    POST endpoint: Nhận link kênh Douyin và trả về danh sách tất cả video URLs cùng metadata (direct mp4, cover, stats).
    """
    if not payload.url or not payload.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp link kênh Douyin (url).")
        
    try:
        result = await scraper.get_channel_videos(
            channel_url_or_sec_id=payload.url,
            max_count=payload.max_count,
            custom_cookie=payload.cookie
        )
        return ChannelVideosResponse(
            success=True,
            message=f"Đã lấy thành công {result['total_collected']} video từ kênh Douyin.",
            data=result,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Lỗi khi cào dữ liệu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi nội bộ khi cào kênh: {str(e)}")

@router.get(
    "/channel/videos",
    response_model=ChannelVideosResponse,
    tags=["Channel Full Details"],
    summary="Lấy toàn bộ video + link MP4 tải trực tiếp + metadata (GET)",
    dependencies=[Depends(check_api_key)]
)
async def get_channel_videos_get(
    url: str = Query(..., description="Link kênh Douyin"),
    max_count: int = Query(50, ge=1, le=500, description="Số lượng video tối đa"),
    cookie: Optional[str] = Query(None, description="Cookie tùy chọn")
):
    """
    GET endpoint: Thuận tiện gọi nhanh qua URL query params.
    """
    payload = ChannelVideosRequest(url=url, max_count=max_count, cookie=cookie)
    return await get_channel_videos_post(payload)

@router.post(
    "/video/urls",
    response_model=VideoUrlsOnlyResponse,
    tags=["Video URLs"],
    summary="Chỉ lấy danh sách URL video (POST - Tối giản cho Bot / Script)",
    dependencies=[Depends(check_api_key)]
)
async def get_video_urls_only_post(payload: ChannelVideosRequest):
    """
    POST endpoint tối giản: Chỉ trả về danh sách URL video (dạng `https://www.douyin.com/video/...`).
    """
    if not payload.url or not payload.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp link kênh Douyin (url).")
    try:
        result = await scraper.get_channel_videos(
            channel_url_or_sec_id=payload.url,
            max_count=payload.max_count,
            custom_cookie=payload.cookie
        )
        return VideoUrlsOnlyResponse(
            success=True,
            total=result["total_collected"],
            sec_user_id=result["sec_user_id"],
            video_urls=result["video_urls"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Lỗi khi cào URL video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/video/urls",
    response_model=VideoUrlsOnlyResponse,
    tags=["Video URLs"],
    summary="Chỉ lấy danh sách URL video (GET - Gọi nhanh qua URL)",
    dependencies=[Depends(check_api_key)]
)
async def get_video_urls_only_get(
    url: str = Query(..., description="Link kênh Douyin"),
    max_count: int = Query(50, ge=1, le=500)
):
    """
    Endpoint tối giản: Chỉ trả về danh sách URL video để tích hợp vào script/tool khác.
    """
    payload = ChannelVideosRequest(url=url, max_count=max_count)
    return await get_video_urls_only_post(payload)
