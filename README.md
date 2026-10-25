# Douyin Channel Video Scraper REST API (Tự Host)

Hệ thống REST API tự host 100% (không phụ thuộc bất kỳ dịch vụ bên thứ 3 nào), tự động giải mã và lấy toàn bộ danh sách URL video từ link kênh Douyin bất kỳ (hỗ trợ link rút gọn `v.douyin.com`, link web `douyin.com/user/...`, hoặc văn bản chia sẻ).

---

## 🚀 Thông tin dịch vụ & Endpoints

- **Host IP**: `http://162.4.177.109:8088` (hoặc `http://localhost:8088`)
- **Web UI & Test Trực Tiếp**: `http://162.4.177.109:8088/`
- **Swagger API Docs**: `http://162.4.177.109:8088/docs`
- **Systemd Service**: `douyin-api.service` (Tự động khởi động cùng hệ thống 24/7)

---

## 📌 Danh sách Endpoints

### 1. Lấy danh sách video (POST)
**Endpoint**: `POST /api/douyin/channel/videos`

**Headers**: `Content-Type: application/json`

**Body JSON**:
```json
{
  "url": "https://v.douyin.com/idFqvUms/",
  "max_count": 50,
  "cookie": null
}
```

**Ví dụ cURL**:
```bash
curl -X POST "http://162.4.177.109:8088/api/douyin/channel/videos" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://v.douyin.com/idFqvUms/", "max_count": 50}'
```

---

### 2. Lấy danh sách video (GET)
**Endpoint**: `GET /api/douyin/channel/videos`

**Query Parameters**:
- `url` (bắt buộc): Link kênh Douyin
- `max_count` (tùy chọn, mặc định 50)
- `cookie` (tùy chọn)

**Ví dụ cURL**:
```bash
curl "http://162.4.177.109:8088/api/douyin/channel/videos?url=https://v.douyin.com/idFqvUms/&max_count=20"
```

---

### 3. Chỉ lấy danh sách URLs video (POST & GET - Tối giản cho Bot / Script)
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

**Ví dụ cURL (GET)**:
```bash
curl "http://162.4.177.109:8088/api/douyin/video/urls?url=https://v.douyin.com/K6959nsbQgs/&max_count=50"
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

### 4. Kiểm tra sức khỏe hệ thống (Health Check)
**Endpoint**: `GET /health`

---

## 🍪 Cấu hình Cookie mặc định trên Server (Khách không cần truyền Cookie)

Để mọi khách gọi API lấy được 200+ hoặc toàn bộ video mà không cần tự cung cấp Cookie:
1. Đăng nhập Douyin trên trình duyệt máy tính của bạn (https://www.douyin.com).
2. Mở DevTools (`F12`) -> Tab **Network** hoặc **Application** -> sao chép chuỗi `Cookie`.
3. Dán toàn bộ chuỗi cookie vào file `/root/douyin/cookie.txt`:
   ```bash
   nano /root/douyin/cookie.txt
   # Dán cookie vào và lưu file
   ```
4. Khởi động lại dịch vụ:
   ```bash
   systemctl restart douyin-api
   ```
*Khi đó, bất kỳ khách nào gọi API chỉ cần gửi link kênh, server sẽ tự động dùng Cookie này để cào đủ 200+ video mà khách không hề biết cookie của bạn.*

---

## ☁️ Hướng dẫn Deploy lên Render (render.com)

Dự án đã có sẵn `Dockerfile` (sử dụng base image chính thức của Microsoft Playwright) và file cấu hình `render.yaml`.

### Cách 1: Deploy qua giao diện Render (Khuyên dùng)
1. Đăng nhập vào [Render.com](https://dashboard.render.com/).
2. Nhấn **New +** $\rightarrow$ chọn **Web Service**.
3. Kết nối tài khoản GitHub và chọn repository **`ToolNetWorks/douyin-api`**.
4. Cấu hình dịch vụ:
   * **Language / Runtime**: Chọn **Docker** (Render sẽ tự động đọc `Dockerfile`).
   * **Region**: Singapore (hoặc Oregon/Frankfurt).
   * **Instance Type**: Free (hoặc Starter).
5. Thêm biến môi trường (**Environment Variables**):
   * `PORT`: `10000` (Render tự động cấp)
   * `DOUYIN_COOKIE` (Tùy chọn): Dán chuỗi cookie tài khoản Douyin vào đây nếu muốn Render tự động cào 200+ video mà khách không cần truyền cookie.
6. Nhấn **Deploy Web Service** và đợi Render build xong là có ngay link public `https://<ten-app>.onrender.com`.

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
