# Douyin Channel Video Scraper REST API (Tự Host)

Hệ thống REST API tự host 100% (không phụ thuộc bất kỳ dịch vụ bên thứ 3 nào), tự động giải mã và lấy toàn bộ danh sách URL video từ link kênh Douyin bất kỳ (hỗ trợ link rút gọn `v.douyin.com`, link web `douyin.com/user/...`, hoặc văn bản chia sẻ).

---

## 📁 Cấu trúc dự án (Architecture)

```text
.
├── services/
│   └── douyin-api/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py                # FastAPI app entrypoint, middleware, lifespan
│       │   ├── core/
│       │   │   ├── __init__.py
│       │   │   └── config.py          # Centralized configuration & search paths
│       │   └── modules/
│       │       └── douyin/
│       │           ├── __init__.py
│       │           ├── router.py      # REST API endpoints & API Key dependency
│       │           ├── scraper.py     # Chromium stealth scraper & auto-scroller
│       │           └── schemas.py     # Pydantic request & response schemas
│       ├── requirements.txt           # Service dependencies
│       └── Dockerfile                 # Standalone service Dockerfile
├── .dockerignore
├── .gitignore
├── Dockerfile                         # Root Dockerfile (hỗ trợ Render context linh hoạt)
├── render.yaml                        # Render Blueprint configuration
└── README.md
```

---

## 🚀 Thông tin dịch vụ & Endpoints

- **VPS Host**: `http://162.4.177.109:8088` (hoặc `http://localhost:8088`)
- **Render Host**: `https://douyin-api-8xzt.onrender.com`
- **Web UI & Test Trực Tiếp**: `/`
- **Swagger API Docs**: `/docs`
- **ReDoc API Docs**: `/redoc`
- **Health Check**: `GET /health`
- **Systemd Service trên VPS**: `douyin-api.service`

---

## 📌 Danh sách Endpoints

### 1. Chỉ lấy danh sách URLs video (POST & GET - Tối giản cho Bot / Script)
**Endpoint**: `POST /api/douyin/video/urls` hoặc `GET /api/douyin/video/urls`

**Ví dụ cURL (POST)**:
```bash
curl -X POST "http://162.4.177.109:8088/api/douyin/video/urls" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://v.douyin.com/K6959nsbQgs/",
    "max_count": 50
  }'
```

**Response mẫu**:
```json
{
  "success": true,
  "total": 50,
  "sec_user_id": "MS4wLjABAAAAqWADWdwOEl2cGKeEOFWgF_6pN5veHym-jvOCePDfJ9s",
  "video_urls": [
    "https://www.douyin.com/video/7429621371077758258",
    "https://www.douyin.com/video/7421832048555232538",
    "https://www.douyin.com/video/7419614742416559395"
  ]
}
```

---

### 2. Lấy toàn bộ video + Metadata + Link MP4 trực tiếp (POST & GET)
**Endpoint**: `POST /api/douyin/channel/videos` hoặc `GET /api/douyin/channel/videos`

**Body JSON**:
```json
{
  "url": "https://v.douyin.com/idFqvUms/",
  "max_count": 50,
  "cookie": null
}
```

**Ví dụ cURL (POST)**:
```bash
curl -X POST "http://162.4.177.109:8088/api/douyin/channel/videos" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://v.douyin.com/idFqvUms/", "max_count": 50}'
```

---

### 3. Kiểm tra sức khỏe hệ thống (Health Check)
**Endpoint**: `GET /health`

---

## 🔐 Bảo mật API Key (Tùy chọn)

Nếu bạn cấu hình biến môi trường `API_KEY` trên server hoặc Render:
* Mọi request đến các endpoint cào video phải truyền key qua một trong ba cách:
  * **Header**: `X-API-Key: <your_key>`
  * **Bearer**: `Authorization: Bearer <your_key>`
  * **Query**: `?api_key=<your_key>`
* Nếu không cài đặt biến `API_KEY`, API sẽ tự động mở tự do (public).

---

## 🍪 Cấu hình Cookie mặc định trên Server (Khách không cần truyền Cookie)

Để mọi khách gọi API lấy được 200+ hoặc toàn bộ video mà không cần tự cung cấp Cookie:
1. Đăng nhập Douyin trên trình duyệt máy tính của bạn (https://www.douyin.com).
2. Mở DevTools (`F12`) -> Tab **Network** hoặc **Application** -> sao chép chuỗi `Cookie`.
3. Dán toàn bộ chuỗi cookie vào file `/root/douyin/cookie.txt` (hoặc biến `DOUYIN_COOKIE` trên Render).
4. Khởi động lại dịch vụ:
   ```bash
   systemctl restart douyin-api
   ```
*Khi đó, bất kỳ khách nào gọi API chỉ cần gửi link kênh, server sẽ tự động dùng Cookie này để cào đủ 200+ video mà khách không hề biết cookie của bạn.*

---

## ☁️ Hướng dẫn Deploy lên Render (render.com)

Dự án đã có sẵn `Dockerfile` chuẩn hóa Playwright Chromium và file cấu hình `render.yaml`.

### Cách Deploy qua giao diện Render:
1. Đăng nhập vào [Render.com](https://dashboard.render.com/).
2. Nhấn **New +** $\rightarrow$ chọn **Web Service**.
3. Kết nối tài khoản GitHub và chọn repository **`ToolNetWorks/douyin-api`**.
4. Cấu hình dịch vụ:
   * **Language / Runtime**: Chọn **Docker**
   * **Dockerfile Path**: `./Dockerfile` (hoặc `services/douyin-api/Dockerfile`)
   * **Region**: Singapore
   * **Instance Type**: Free
5. Thêm biến môi trường (**Environment Variables**):
   * `PORT`: `10000` (Render tự động cấp)
   * `DOUYIN_COOKIE` (Tùy chọn): Dán chuỗi cookie tài khoản Douyin vào đây.
   * `API_KEY` (Tùy chọn): Đặt key bảo mật nếu cần.
6. Nhấn **Deploy Web Service**.

---

## 🛠 Quản lý dịch vụ trên VPS

```bash
# Xem trạng thái dịch vụ
systemctl status douyin-api

# Khởi động lại dịch vụ
systemctl restart douyin-api

# Dừng dịch vụ
systemctl stop douyin-api

# Xem log thời gian thực
journalctl -u douyin-api -f
```
