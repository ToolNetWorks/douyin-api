import logging
import os
from typing import Optional, Dict, Any
import httpx
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
    Xác thực API Key:
    - Hỗ trợ key cấu hình trong ENV `API_KEY` (hỗ trợ nhiều key cách nhau bằng dấu phẩy).
    - Hỗ trợ key tạm dùng để test: `douyin_test_2026`.
    - Nếu server không cài API_KEY thì cho phép truy cập tự do.
    """
    allowed_keys = {"douyin_test_2026"}
    if settings.API_KEY:
        for k in settings.API_KEY.split(","):
            if k.strip():
                allowed_keys.add(k.strip())
    else:
        return True

    token = x_api_key or api_key
    if not token and "authorization" in request.headers:
        auth = request.headers["authorization"]
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            
    if token not in allowed_keys:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: API Key không hợp lệ. Vui lòng truyền qua Header 'X-API-Key' hoặc Query '?api_key=...'"
        )
    return True

async def call_scraper_or_upstream(payload: ChannelVideosRequest) -> Dict[str, Any]:
    upstream_url = os.environ.get("UPSTREAM_URL", "").strip().rstrip("/")
    if upstream_url:
        logger.info(f"Forwarding scrape request to upstream VPS: {upstream_url}")
        try:
            async with httpx.AsyncClient(timeout=85.0) as client:
                resp = await client.post(
                    f"{upstream_url}/api/douyin/channel/videos",
                    json={"url": payload.url, "max_count": payload.max_count, "cookie": payload.cookie},
                    headers={"X-API-Key": "douyin_test_2026"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", data)
                else:
                    logger.warning(f"Upstream returned status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Failed to forward to upstream: {e}, falling back to local scraper")

    return await scraper.get_channel_videos(
        channel_url_or_sec_id=payload.url,
        max_count=payload.max_count,
        custom_cookie=payload.cookie
    )

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
        result = await call_scraper_or_upstream(payload)
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
        result = await call_scraper_or_upstream(payload)
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
