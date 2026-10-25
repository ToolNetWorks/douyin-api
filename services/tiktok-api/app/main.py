import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.modules.tiktok.router import router as tiktok_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tiktok_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Khởi động TikTok Video Scraper API v1.0.0...")
    yield
    logger.info("Dừng TikTok Video Scraper API...")

app = FastAPI(
    title="TikTok Video Scraper REST API",
    description="REST API độc lập hỗ trợ thu thập danh sách URL và metadata video từ tài khoản TikTok công khai.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tiktok_router)

@app.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint cho Render và monitoring uptime."""
    return {
        "status": "healthy",
        "service": "tiktok-api",
        "version": "1.0.0",
        "api_key_configured": bool(settings.API_KEY),
    }

@app.get("/", response_class=HTMLResponse, summary="Giao diện kiểm thử TikTok API")
async def index():
    """Giao diện Dashboard kiểm thử cào video TikTok."""
    return """
<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Video Scraper Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        tiktok: {
                            cyan: '#25F4EE',
                            pink: '#FE2C55',
                            dark: '#010101',
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
    <div class="max-w-6xl mx-auto px-4 py-8">
        <!-- Header -->
        <header class="flex flex-col md:flex-row items-center justify-between pb-6 mb-8 border-b border-slate-800 gap-4">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-tiktok-pink to-tiktok-cyan flex items-center justify-center font-black text-xl text-black">
                    TT
                </div>
                <div>
                    <h1 class="text-2xl font-bold tracking-tight">TikTok Video Scraper API</h1>
                    <p class="text-sm text-slate-400">Trích xuất danh sách URL & metadata video từ tài khoản TikTok công khai</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <a href="/docs" target="_blank" class="px-4 py-2 text-sm font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors">
                    Swagger Docs
                </a>
                <a href="/health" target="_blank" class="px-4 py-2 text-sm font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 rounded-lg">
                    ● Health Check
                </a>
            </div>
        </header>

        <!-- Form Card -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-8">
            <form id="scrapeForm" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                    <div class="md:col-span-6">
                        <label class="block text-xs font-semibold text-slate-400 mb-1">URL KÊNH HOẶC TÀI KHOẢN TIKTOK</label>
                        <input type="text" id="channelUrl" required placeholder="https://www.tiktok.com/@username hoặc @username hoặc link vt.tiktok.com" 
                            class="w-full px-4 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:border-tiktok-cyan text-sm">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-400 mb-1">SỐ LƯỢNG (MAX)</label>
                        <input type="number" id="maxCount" value="30" min="1" max="500" 
                            class="w-full px-4 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:border-tiktok-cyan text-sm">
                    </div>
                    <div class="md:col-span-4">
                        <label class="block text-xs font-semibold text-slate-400 mb-1">API KEY (LƯU TRÊN TRÌNH DUYỆT)</label>
                        <input type="password" id="apiKeyInput" placeholder="Nhập API Key để xác thực" 
                            class="w-full px-4 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:border-tiktok-cyan text-sm">
                    </div>
                </div>

                <div class="flex items-center justify-between pt-2">
                    <div class="text-xs text-slate-500">
                        Hỗ trợ link web, link rút gọn <code class="text-tiktok-cyan">vt.tiktok.com</code>, <code class="text-tiktok-cyan">vm.tiktok.com</code> hoặc tên <code class="text-tiktok-pink">@username</code>.
                    </div>
                    <button type="submit" id="submitBtn" 
                        class="px-6 py-2.5 bg-gradient-to-r from-tiktok-pink to-rose-600 hover:from-rose-500 hover:to-pink-600 text-white font-bold rounded-xl shadow-lg transition-all flex items-center gap-2">
                        <span id="btnText">Bắt đầu Cào Video</span>
                        <svg id="btnSpinner" class="hidden animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                        </svg>
                    </button>
                </div>
            </form>
        </div>

        <!-- Alert messages -->
        <div id="errorAlert" class="hidden mb-6 p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-sm"></div>

        <!-- Author info & stats -->
        <div id="authorBox" class="hidden mb-6 bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-4">
                <img id="authorAvatar" src="" class="w-16 h-16 rounded-full border-2 border-tiktok-cyan object-cover bg-slate-800">
                <div>
                    <h2 id="authorName" class="text-lg font-bold"></h2>
                    <p id="authorUser" class="text-sm text-tiktok-cyan"></p>
                    <p id="authorBio" class="text-xs text-slate-400 mt-1 max-w-md line-clamp-1"></p>
                </div>
            </div>
            <div class="flex items-center gap-6 text-center">
                <div>
                    <div id="authorFollowers" class="text-base font-bold text-slate-200">0</div>
                    <div class="text-xs text-slate-500">Followers</div>
                </div>
                <div>
                    <div id="authorLikes" class="text-base font-bold text-slate-200">0</div>
                    <div class="text-xs text-slate-500">Hearts</div>
                </div>
                <div>
                    <div id="authorWorks" class="text-base font-bold text-slate-200">0</div>
                    <div class="text-xs text-slate-500">Videos</div>
                </div>
            </div>
        </div>

        <!-- Results section -->
        <div id="resultsSection" class="hidden space-y-6">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div class="text-sm">
                    Đã thu thập: <span id="collectedCount" class="font-bold text-tiktok-cyan text-base">0</span> video
                </div>
                <div class="flex items-center gap-3">
                    <button id="copyUrlsBtn" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors flex items-center gap-2">
                        📋 Copy Toàn bộ URL (<span id="copyCount">0</span>)
                    </button>
                </div>
            </div>

            <!-- Video Grid -->
            <div id="videoGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"></div>
        </div>
    </div>

    <script>
        const form = document.getElementById('scrapeForm');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const btnSpinner = document.getElementById('btnSpinner');
        const errorAlert = document.getElementById('errorAlert');
        const authorBox = document.getElementById('authorBox');
        const resultsSection = document.getElementById('resultsSection');
        const videoGrid = document.getElementById('videoGrid');
        const copyUrlsBtn = document.getElementById('copyUrlsBtn');
        const apiKeyInput = document.getElementById('apiKeyInput');

        let currentUrls = [];

        // Load saved API key from localStorage
        const savedKey = localStorage.getItem('tiktok_api_key');
        if (savedKey) {
            apiKeyInput.value = savedKey;
        }

        apiKeyInput.addEventListener('change', () => {
            if (apiKeyInput.value.trim()) {
                localStorage.setItem('tiktok_api_key', apiKeyInput.value.trim());
            } else {
                localStorage.removeItem('tiktok_api_key');
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            errorAlert.classList.add('hidden');
            authorBox.classList.add('hidden');
            resultsSection.classList.add('hidden');
            videoGrid.innerHTML = '';
            currentUrls = [];

            const url = document.getElementById('channelUrl').value.trim();
            const maxCount = parseInt(document.getElementById('maxCount').value) || 30;
            const apiKey = apiKeyInput.value.trim();

            if (!apiKey) {
                errorAlert.textContent = 'Vui lòng nhập API Key để thực hiện crawl.';
                errorAlert.classList.remove('hidden');
                return;
            }

            submitBtn.disabled = true;
            btnText.textContent = 'Đang cào video...';
            btnSpinner.classList.remove('hidden');

            try {
                const response = await fetch('/api/tiktok/channel/videos', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': apiKey,
                    },
                    body: JSON.stringify({ url, max_count: maxCount })
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.message || data.detail || 'Có lỗi xảy ra khi cào dữ liệu.');
                }

                // Render Author
                if (data.author) {
                    document.getElementById('authorAvatar').src = data.author.avatar || '';
                    document.getElementById('authorName').textContent = data.author.nickname || data.username;
                    document.getElementById('authorUser').textContent = '@' + (data.author.unique_id || data.username);
                    document.getElementById('authorBio').textContent = data.author.signature || 'Chưa có tiểu sử';
                    document.getElementById('authorFollowers').textContent = (data.author.follower_count || 0).toLocaleString();
                    document.getElementById('authorLikes').textContent = (data.author.heart_count || 0).toLocaleString();
                    document.getElementById('authorWorks').textContent = (data.author.video_count || 0).toLocaleString();
                    authorBox.classList.remove('hidden');
                }

                // Render Videos
                currentUrls = data.video_urls || [];
                document.getElementById('collectedCount').textContent = data.total_collected;
                document.getElementById('copyCount').textContent = currentUrls.length;

                if (data.videos && data.videos.length > 0) {
                    data.videos.forEach(v => {
                        const card = document.createElement('div');
                        card.className = 'bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-colors flex flex-col';
                        
                        const coverImg = v.cover_url ? `<img src="${v.cover_url}" class="w-full h-44 object-cover bg-slate-950" loading="lazy">` : `<div class="w-full h-44 bg-slate-950 flex items-center justify-center text-slate-700">No Cover</div>`;
                        
                        card.innerHTML = `
                            ${coverImg}
                            <div class="p-4 flex-1 flex flex-col justify-between">
                                <div>
                                    <h3 class="text-sm font-medium text-slate-200 line-clamp-2 mb-2" title="${v.title || ''}">${v.title || 'Không có tiêu đề'}</h3>
                                </div>
                                <div class="pt-3 border-t border-slate-800/80">
                                    <div class="flex items-center justify-between text-xs text-slate-400 mb-3">
                                        <span>👁️ ${(v.views || 0).toLocaleString()}</span>
                                        <span>❤️ ${(v.likes || 0).toLocaleString()}</span>
                                        <span>⏱️ ${v.duration_seconds || 0}s</span>
                                    </div>
                                    <a href="${v.url}" target="_blank" class="block text-center py-1.5 px-3 bg-slate-800 hover:bg-tiktok-pink hover:text-white text-xs font-semibold rounded-lg text-slate-300 transition-colors">
                                        Xem Video Trên TikTok ↗
                                    </a>
                                </div>
                            </div>
                        `;
                        videoGrid.appendChild(card);
                    });
                }

                resultsSection.classList.remove('hidden');
            } catch (err) {
                errorAlert.textContent = err.message || 'Lỗi không xác định.';
                errorAlert.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                btnText.textContent = 'Bắt đầu Cào Video';
                btnSpinner.classList.add('hidden');
            }
        });

        copyUrlsBtn.addEventListener('click', () => {
            if (!currentUrls.length) return;
            navigator.clipboard.writeText(currentUrls.join('\\n')).then(() => {
                const originalText = copyUrlsBtn.innerHTML;
                copyUrlsBtn.innerHTML = '✅ Đã Copy vào Clipboard!';
                setTimeout(() => { copyUrlsBtn.innerHTML = originalText; }, 2000);
            });
        });
    </script>
</body>
</html>
    """
