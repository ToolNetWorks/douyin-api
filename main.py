import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from scraper import DouyinScraper, resolve_douyin_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("douyin_api")

app = FastAPI(
    title="Douyin Channel Video Scraper API",
    description="REST API tự host để lấy toàn bộ URL video của một kênh Douyin từ link kênh (hỗ trợ cả link rút gọn v.douyin.com, link chia sẻ, link web). Không phụ thuộc bên thứ 3.",
    version="1.0.0",
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraper = DouyinScraper()

@app.on_event("shutdown")
async def shutdown_event():
    await scraper.close()

# Request Models
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

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "douyin-channel-scraper-api",
        "version": "1.0.0",
        "self_hosted": True,
    }

@app.post(
    "/api/douyin/channel/videos",
    response_model=ChannelVideosResponse,
    tags=["Channel Full Details"],
    summary="Lấy toàn bộ video + link MP4 tải trực tiếp + metadata (POST)"
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

@app.get(
    "/api/douyin/channel/videos",
    response_model=ChannelVideosResponse,
    tags=["Channel Full Details"],
    summary="Lấy toàn bộ video + link MP4 tải trực tiếp + metadata (GET)"
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

@app.post(
    "/api/douyin/video/urls",
    tags=["Video URLs"],
    summary="Chỉ lấy danh sách URL video (POST - Tối giản cho Bot / Script)"
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
        return {
            "success": True,
            "total": result["total_collected"],
            "sec_user_id": result["sec_user_id"],
            "video_urls": result["video_urls"]
        }
    except Exception as e:
        logger.error(f"Lỗi khi cào URL video: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get(
    "/api/douyin/video/urls",
    tags=["Video URLs"],
    summary="Chỉ lấy danh sách URL video (GET - Gọi nhanh qua URL)"
)
async def get_video_urls_only(
    url: str = Query(..., description="Link kênh Douyin"),
    max_count: int = Query(50, ge=1, le=500)
):
    """
    Endpoint tối giản: Chỉ trả về danh sách URL video để tích hợp vào script/tool khác.
    """
    try:
        result = await scraper.get_channel_videos(
            channel_url_or_sec_id=url,
            max_count=max_count
        )
        return {
            "success": True,
            "total": result["total_collected"],
            "sec_user_id": result["sec_user_id"],
            "video_urls": result["video_urls"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def home():
    """
    Giao diện web trực quan để test và gọi API trực tiếp trên trình duyệt.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Douyin Channel Video Scraper API</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen py-10 px-4">
        <div class="max-w-4xl mx-auto space-y-6">
            <div class="text-center space-y-2">
                <div class="inline-flex items-center space-x-2 bg-rose-500/10 text-rose-400 px-4 py-1.5 rounded-full text-sm font-medium border border-rose-500/20">
                    <i class="fab fa-tiktok"></i>
                    <span>Tự Host 100% - Không Dùng Bên Thứ 3</span>
                </div>
                <h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight">
                    Douyin Channel Video Scraper API
                </h1>
                <p class="text-slate-400 text-sm sm:text-base">
                    Nhập link kênh Douyin bất kỳ (link rút gọn <code class="text-rose-400">v.douyin.com</code> hoặc link web) để lấy toàn bộ link video.
                </p>
            </div>

            <!-- Card Demo Tester -->
            <div class="bg-slate-800/90 border border-slate-700 rounded-2xl p-6 shadow-xl backdrop-blur">
                <form id="scrapeForm" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-1">Link Kênh Douyin</label>
                        <input type="text" id="channelUrl" required placeholder="https://v.douyin.com/idFqvUms/ hoặc https://www.douyin.com/user/..." 
                               class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent transition">
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1">Số lượng video tối đa</label>
                            <input type="number" id="maxCount" value="50" min="1" max="500" 
                                   class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1">Cookie tùy chọn (Không bắt buộc)</label>
                            <input type="text" id="cookie" placeholder="sessionid=... hoặc để trống" 
                                   class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500">
                        </div>
                    </div>
                    <button type="submit" id="submitBtn" 
                            class="w-full bg-gradient-to-r from-rose-500 to-pink-600 hover:from-rose-600 hover:to-pink-700 text-white font-semibold py-3 px-6 rounded-xl transition duration-200 flex items-center justify-center space-x-2 shadow-lg shadow-rose-500/25">
                        <i class="fas fa-search"></i>
                        <span>Lấy Danh Sách Video</span>
                    </button>
                </form>

                <!-- Loading State -->
                <div id="loading" class="hidden my-8 text-center space-y-3">
                    <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-rose-500 border-t-transparent"></div>
                    <p class="text-sm text-slate-400">Đang khởi chạy trình duyệt stealth & cào dữ liệu kênh Douyin... (khoảng 8-12 giây)</p>
                </div>

                <!-- Result Box -->
                <div id="resultBox" class="hidden mt-6 space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-700 pb-3">
                        <div id="authorHeader" class="flex items-center space-x-3"></div>
                        <span id="videoCountBadge" class="bg-rose-500/20 text-rose-400 font-bold px-3 py-1 rounded-full text-xs"></span>
                    </div>

                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-semibold text-slate-300">Danh Sách Video URLs:</span>
                            <button onclick="copyAllUrls()" class="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded-lg text-slate-200 transition">
                                <i class="far fa-copy mr-1"></i>Copy Tất Cả URLs
                            </button>
                        </div>
                        <textarea id="urlsOutput" rows="5" readonly class="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 font-mono text-xs text-rose-300 select-all"></textarea>
                    </div>

                    <div class="space-y-2">
                        <span class="text-sm font-semibold text-slate-300">Chi tiết video:</span>
                        <div id="videoCards" class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1"></div>
                    </div>
                </div>
            </div>

            <!-- API Docs Info Card -->
            <div class="bg-slate-800/60 border border-slate-700/80 rounded-2xl p-6 space-y-4">
                <div class="flex items-center justify-between">
                    <h2 class="text-lg font-bold flex items-center space-x-2">
                        <i class="fas fa-terminal text-rose-400"></i>
                        <span>Hướng Dẫn Sử Dụng REST API</span>
                    </h2>
                    <a href="/docs" target="_blank" class="text-xs bg-rose-600 hover:bg-rose-500 text-white font-medium px-3 py-1.5 rounded-lg transition">
                        Mở Swagger UI Docs <i class="fas fa-external-link-alt ml-1"></i>
                    </a>
                </div>

                <div class="space-y-3 font-mono text-xs">
                    <div>
                        <p class="text-slate-400 mb-1">1. Lấy danh sách video (POST JSON):</p>
                        <pre class="bg-slate-950 p-3 rounded-lg text-emerald-400 overflow-x-auto">curl -X POST "http://162.4.177.109:8088/api/douyin/channel/videos" \\
     -H "Content-Type: application/json" \\
     -d '{"url": "https://v.douyin.com/idFqvUms/", "max_count": 50}'</pre>
                    </div>

                    <div>
                        <p class="text-slate-400 mb-1">2. Lấy nhanh qua GET Query:</p>
                        <pre class="bg-slate-950 p-3 rounded-lg text-emerald-400 overflow-x-auto">curl "http://162.4.177.109:8088/api/douyin/channel/videos?url=https://v.douyin.com/idFqvUms/&max_count=20"</pre>
                    </div>

                    <div>
                        <p class="text-slate-400 mb-1">3. Chỉ lấy danh sách URLs video (thuần URL):</p>
                        <pre class="bg-slate-950 p-3 rounded-lg text-emerald-400 overflow-x-auto">curl "http://162.4.177.109:8088/api/douyin/video/urls?url=https://v.douyin.com/idFqvUms/"</pre>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentUrls = [];
            const form = document.getElementById('scrapeForm');
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const resultBox = document.getElementById('resultBox');

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const url = document.getElementById('channelUrl').value.trim();
                const max_count = parseInt(document.getElementById('maxCount').value) || 50;
                const cookie = document.getElementById('cookie').value.trim() || undefined;

                submitBtn.disabled = true;
                submitBtn.classList.add('opacity-50');
                loading.classList.remove('hidden');
                resultBox.classList.add('hidden');

                try {
                    const resp = await fetch('/api/douyin/channel/videos', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url, max_count, cookie })
                    });
                    const res = await resp.json();
                    if (!resp.ok) {
                        alert('Lỗi: ' + (res.detail || 'Không thể cào dữ liệu'));
                        return;
                    }

                    const data = res.data;
                    currentUrls = data.video_urls || [];
                    document.getElementById('urlsOutput').value = currentUrls.join('\\n');
                    document.getElementById('videoCountBadge').innerText = `${data.total_collected} Videos`;

                    const author = data.author || {};
                    document.getElementById('authorHeader').innerHTML = `
                        <div class="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center font-bold text-rose-400 text-lg border border-slate-600">
                            ${(author.nickname ? author.nickname[0] : 'D')}
                        </div>
                        <div>
                            <div class="font-bold text-sm text-slate-100">${author.nickname || 'Kênh Douyin'}</div>
                            <div class="text-xs text-slate-400 font-mono">Sec UID: ${data.sec_user_id.slice(0, 18)}...</div>
                        </div>
                    `;

                    const cardsDiv = document.getElementById('videoCards');
                    cardsDiv.innerHTML = '';
                    (data.videos || []).forEach((v) => {
                        const card = document.createElement('div');
                        card.className = "bg-slate-900 border border-slate-800 rounded-xl p-3 flex space-x-3 items-start";
                        card.innerHTML = `
                            ${v.cover_url ? `<img src="${v.cover_url}" class="w-16 h-20 object-cover rounded-lg flex-shrink-0 bg-slate-800">` : ''}
                            <div class="flex-1 min-w-0 space-y-1">
                                <p class="text-xs font-medium text-slate-200 line-clamp-2">${v.title || 'Không có tiêu đề'}</p>
                                <div class="flex items-center space-x-2 text-[10px] text-slate-400">
                                    <span><i class="far fa-heart mr-1"></i>${(v.stats?.likes || 0).toLocaleString()}</span>
                                    <span><i class="far fa-clock mr-1"></i>${v.duration_seconds}s</span>
                                </div>
                                <div class="pt-1 flex space-x-2">
                                    <a href="${v.url}" target="_blank" class="text-[11px] text-rose-400 hover:underline">Link Douyin <i class="fas fa-external-link-alt text-[9px]"></i></a>
                                    ${v.play_url ? `<a href="${v.play_url}" target="_blank" class="text-[11px] text-emerald-400 hover:underline">Direct MP4</a>` : ''}
                                </div>
                            </div>
                        `;
                        cardsDiv.appendChild(card);
                    });

                    resultBox.classList.remove('hidden');
                } catch (err) {
                    alert('Lỗi kết nối API: ' + err.message);
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-50');
                    loading.classList.add('hidden');
                }
            });

            function copyAllUrls() {
                const ta = document.getElementById('urlsOutput');
                ta.select();
                navigator.clipboard.writeText(ta.value);
                alert('Đã copy ' + currentUrls.length + ' video URLs vào clipboard!');
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=False)
