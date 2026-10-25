# TikTok Video Scraper REST API

Hệ thống REST API độc lập, tự host 100% (không phụ thuộc RapidAPI hoặc bên thứ 3 trả phí) để thu thập danh sách URL video và metadata từ bất kỳ tài khoản TikTok công khai nào.

## 🚀 Tính năng nổi bật
* **100% Lightweight HTTP Scraper**: Tối ưu tài nguyên cực thấp (~50-80 MB RAM), hoàn toàn phù hợp với gói Render Free (512 MB RAM, 0.1 CPU).
* **Không cần headless browser cồng kềnh**: Bỏ qua Playwright / Chromium nặng nề, khởi động tức thì và không bị OOM.
* **Hỗ trợ đa dạng link đầu vào**:
  * `https://www.tiktok.com/@username`
  * `@username`
  * Link rút gọn: `https://vt.tiktok.com/...`, `https://vm.tiktok.com/...`
  * Link video: `https://www.tiktok.com/@username/video/123456789...`
* **Trích xuất metadata đầy đủ**:
  * Tác giả: Nickname, Unique ID, SecUID, Avatar, Bio, Followers, Following, Likes, Tổng số video.
  * Video: ID, URL, Tiêu đề/Mô tả, Ảnh bìa (Cover), Thời lượng (giây), Lượt xem (views), Thích (likes), Bình luận (comments), Chia sẻ (shares), Lưu (bookmarks).
* **Phân trang thông minh**: Hỗ trợ lấy lên tới hàng trăm video qua cơ chế cursor lùi thời gian.
* **Bảo mật**:
  * Bắt buộc xác thực `X-API-Key` hoặc `Authorization: Bearer <key>`.
  * Cơ chế chống SSRF (chặn truy cập loopback / IP nội bộ).
  * Giới hạn cào đồng thời (`MAX_CONCURRENT_CRAWLS=1`).

---

## 📡 Danh sách Endpoints

| Method | Endpoint | Mô tả | Yêu cầu API Key |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Kiểm tra trạng thái hoạt động service | Không |
| `GET` | `/` | Giao diện Dashboard kiểm thử tương tác | Không |
| `GET` | `/docs` | Swagger OpenAPI Documentation | Không |
| `POST` | `/api/tiktok/channel/videos` | Lấy danh sách video kèm metadata đầy đủ | **Có** |
| `GET` | `/api/tiktok/channel/videos` | Dạng GET của endpoint trên | **Có** |
| `POST` | `/api/tiktok/video/urls` | Chỉ trả về danh sách URL video | **Có** |
| `GET` | `/api/tiktok/video/urls` | Dạng GET của endpoint trên | **Có** |
| `GET` | `/api/tiktok/video/info` | Lấy metadata chi tiết 1 video | **Có** |

---

## 🛠 Hướng dẫn Triển khai trên Render Free

### Bước 1: Tạo Web Service mới
1. Đăng nhập [Render Dashboard](https://dashboard.render.com).
2. Chọn **New +** -> **Web Service**.
3. Chọn Git Provider và kết nối repository: `ToolNetWorks/douyin-api`.

### Bước 2: Cấu hình thông số
* **Name**: `tiktok-api`
* **Region**: `Singapore`
* **Branch**: `main`
* **Root Directory**: `services/tiktok-api`
* **Runtime**: `Docker`
* **Dockerfile Path**: `./Dockerfile`
* **Instance Type**: `Free`

### Bước 3: Cấu hình Environment Variables
Thêm các biến môi trường tại mục **Environment Variables**:
* `API_KEY`: *(Nhập mã bí mật của bạn, ví dụ: `my_tiktok_secret_key`)*
* `PORT`: `10000`
* `MAX_CONCURRENT_CRAWLS`: `1`

Bấm **Create Web Service** để bắt đầu build và deploy.

---

## 💻 Ví dụ Gọi API bằng cURL

### 1. Cào danh sách URL video:
```bash
curl -sS -X POST "https://your-tiktok-service.onrender.com/api/tiktok/video/urls" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tiktok.com/@khaby.lame",
    "max_count": 20
  }'
```

### 2. Cào video kèm metadata đầy đủ:
```bash
curl -sS -X POST "https://your-tiktok-service.onrender.com/api/tiktok/channel/videos" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "@khaby.lame",
    "max_count": 30
  }'
```

### 3. Lấy thông tin 1 video đơn lẻ:
```bash
curl -sS -X GET "https://your-tiktok-service.onrender.com/api/tiktok/video/info?url=https://www.tiktok.com/@tiktok/video/7700680369246358815" \
  -H "X-API-Key: YOUR_API_KEY"
```
