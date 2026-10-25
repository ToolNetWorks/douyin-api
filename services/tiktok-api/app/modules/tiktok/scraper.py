import asyncio
import json
import logging
import random
import re
import string
import time
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yt_dlp

from app.core.config import settings

logger = logging.getLogger("tiktok_scraper")

# SSRF Protection: IP patterns that must be blocked
DISALLOWED_IP_PATTERNS = [
    re.compile(r"^127\."),
    re.compile(r"^10\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."),
    re.compile(r"^169\.254\."),
    re.compile(r"^0\."),
    re.compile(r"^::1$"),
    re.compile(r"^fc00:"),
    re.compile(r"^fe80:"),
]

def is_safe_url(url_str: str) -> bool:
    """Kiểm tra URL an toàn chống tấn công SSRF."""
    try:
        parsed = urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host or host in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False
        for pattern in DISALLOWED_IP_PATTERNS:
            if pattern.search(host):
                return False
        # Host must belong to tiktok domains
        if not any(host == h or host.endswith("." + h) for h in settings.ALLOWED_HOSTS):
            return False
        return True
    except Exception:
        return False

def extract_username_from_text(text: str) -> Optional[str]:
    """Trích xuất username từ link hoặc văn bản người dùng nhập."""
    if not text:
        return None
    cleaned = text.strip()
    
    # 1. Nếu là dạng @username hoặc username đơn giản
    if cleaned.startswith("@"):
        return cleaned.lstrip("@").split("/")[0].split("?")[0]
    
    # 2. Tìm pattern @username trong URL
    match = re.search(r"@([a-zA-Z0-9_\.\-]+)", cleaned)
    if match:
        return match.group(1).rstrip("/?#.,;")

    # 3. Nếu là raw username không dấu cách và không có scheme
    if re.fullmatch(r"[a-zA-Z0-9_\.\-]{2,64}", cleaned) and "http" not in cleaned:
        return cleaned

    return None

class TikTokScraper:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CRAWLS)
        self._mobile_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
        )
        self._desktop_ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )

    async def resolve_input_to_username(self, input_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Phân giải input của người dùng (URL rút gọn vt.tiktok.com, link video, hoặc username)
        thành (username, error_code).
        """
        direct_user = extract_username_from_text(input_text)
        if direct_user and "vt.tiktok.com" not in input_text and "vm.tiktok.com" not in input_text:
            return direct_user, None

        # Nếu là link rút gọn hoặc link cần follow redirect
        raw_url = input_text.strip()
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"https://{raw_url}"

        if not is_safe_url(raw_url):
            return None, "INVALID_OR_DISALLOWED_URL"

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                headers = {"User-Agent": self._mobile_ua}
                resp = await client.get(raw_url, headers=headers)
                final_url = str(resp.url)
                
                # Check SSRF on redirected destination
                if not is_safe_url(final_url):
                    return None, "REDIRECT_TO_DISALLOWED_HOST"

                username = extract_username_from_text(final_url)
                if username:
                    return username, None
                
                # Cố gắng tìm trong nội dung nếu có canonical link
                match_canon = re.search(r"<link[^>]+rel=\"canonical\"[^>]+href=\"([^\"]+)\"", resp.text)
                if match_canon:
                    canon_user = extract_username_from_text(match_canon.group(1))
                    if canon_user:
                        return canon_user, None

                return None, "CANNOT_RESOLVE_USERNAME"
        except Exception as e:
            logger.error(f"Lỗi khi resolve URL {input_text}: {e}")
            return None, "REDIRECT_RESOLUTION_FAILED"

    async def get_user_profile(self, username: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Lấy thông tin profile người dùng TikTok qua Mobile Web SSR:
        Trả về (user_info_dict, error_code, error_message).
        """
        url = f"https://www.tiktok.com/@{username}"
        headers = {
            "User-Agent": self._mobile_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    return None, "ACCOUNT_NOT_FOUND", f"Tài khoản TikTok @{username} không tồn tại (HTTP 404)."

                text = resp.text
                match = re.search(r"<script id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\"[^>]*>(.*?)</script>", text)
                if not match:
                    if "verify" in text.lower() or "captcha" in text.lower():
                        return None, "BLOCKED_OR_CAPTCHA", "TikTok yêu cầu xác minh Captcha hoặc chặn truy cập tạm thời."
                    return None, "PARSE_FAILED", "Không tìm thấy dữ liệu SSR cấu trúc của người dùng."

                data = json.loads(match.group(1))
                user_detail = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
                status_code = user_detail.get("statusCode", 0)

                if status_code in (10221, 10202):
                    return None, "ACCOUNT_NOT_FOUND", f"Tài khoản @{username} không tồn tại hoặc đã bị khóa."
                if status_code == 10222:
                    return None, "ACCOUNT_PRIVATE", f"Tài khoản @{username} đang ở chế độ riêng tư (Private)."

                user_info = user_detail.get("userInfo", {})
                user = user_info.get("user", {})
                if not user or not user.get("secUid"):
                    return None, "SEC_UID_NOT_FOUND", "Không tìm thấy mã định danh secUid của tài khoản."

                if user.get("secret") is True:
                    return None, "ACCOUNT_PRIVATE", f"Tài khoản @{username} đang ở chế độ riêng tư (Private)."

                stats = user_info.get("stats", {})
                profile_data = {
                    "nickname": user.get("nickname"),
                    "unique_id": user.get("uniqueId") or username,
                    "sec_uid": user.get("secUid"),
                    "avatar": user.get("avatarThumb") or user.get("avatarMedium") or user.get("avatarLarger"),
                    "signature": user.get("signature"),
                    "follower_count": stats.get("followerCount"),
                    "following_count": stats.get("followingCount"),
                    "heart_count": stats.get("heartCount") or stats.get("heart"),
                    "video_count": stats.get("videoCount", 0),
                }
                return profile_data, None, None
        except httpx.TimeoutException:
            return None, "TIMEOUT", f"Hết thời gian kết nối tới TikTok khi tải profile @{username}."
        except Exception as e:
            logger.error(f"Lỗi khi tải profile @{username}: {e}")
            return None, "INTERNAL_ERROR", str(e)

    async def get_channel_videos(
        self,
        input_url: str,
        max_count: int = 30,
    ) -> Dict[str, Any]:
        """
        Cào danh sách video từ kênh TikTok với phân trang cursor,
        giới hạn đồng thời bằng Semaphore để an toàn tài nguyên.
        """
        max_count = max(1, min(max_count, settings.MAX_ALLOWED_COUNT))

        async with self._semaphore:
            # 1. Phân giải username
            username, err_code = await self.resolve_input_to_username(input_url)
            if not username or err_code:
                return {
                    "success": False,
                    "platform": "tiktok",
                    "username": None,
                    "total_collected": 0,
                    "video_urls": [],
                    "videos": [],
                    "has_more": False,
                    "next_cursor": None,
                    "error_code": err_code or "INVALID_USERNAME",
                    "message": "Không thể xác định tên tài khoản TikTok từ đường link cung cấp.",
                }

            # 2. Lấy profile và sec_uid
            profile, err_code, err_msg = await self.get_user_profile(username)
            if not profile or err_code:
                return {
                    "success": False,
                    "platform": "tiktok",
                    "username": username,
                    "total_collected": 0,
                    "video_urls": [],
                    "videos": [],
                    "has_more": False,
                    "next_cursor": None,
                    "error_code": err_code,
                    "message": err_msg,
                }

            sec_uid = profile["sec_uid"]
            unique_id = profile["unique_id"]

            if profile.get("video_count") == 0:
                return {
                    "success": True,
                    "platform": "tiktok",
                    "username": unique_id,
                    "author": profile,
                    "total_collected": 0,
                    "video_urls": [],
                    "videos": [],
                    "has_more": False,
                    "next_cursor": None,
                    "error_code": None,
                    "message": f"Tài khoản @{unique_id} hiện chưa đăng video nào.",
                }

            # 3. Thu thập video từ API creator/item_list/
            videos_list: List[Dict[str, Any]] = []
            seen_ids = set()
            cursor = int(time.time() * 1000)
            has_more = True
            next_cursor = None
            max_pages = max(1, (max_count // settings.PAGE_SIZE) + 4)
            page_count = 0

            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                while len(videos_list) < max_count and has_more and page_count < max_pages:
                    page_count += 1
                    vfp = f"verify_{''.join(random.choices(string.hexdigits, k=7))}"
                    query = {
                        "aid": "1988",
                        "app_language": "en",
                        "app_name": "tiktok_web",
                        "browser_language": "en-US",
                        "browser_name": "Mozilla",
                        "browser_online": "true",
                        "browser_platform": "Win32",
                        "browser_version": "5.0 (Windows)",
                        "channel": "tiktok_web",
                        "cookie_enabled": "true",
                        "count": str(settings.PAGE_SIZE),
                        "cursor": str(cursor),
                        "device_id": str(random.randint(10**18, 10**19 - 1)),
                        "device_platform": "web_pc",
                        "focus_state": "true",
                        "from_page": "user",
                        "history_len": "2",
                        "is_fullscreen": "false",
                        "is_page_visible": "true",
                        "language": "en",
                        "os": "windows",
                        "region": "US",
                        "screen_height": "1080",
                        "screen_width": "1920",
                        "secUid": sec_uid,
                        "type": "1",
                        "tz_name": "UTC",
                        "verifyFp": vfp,
                        "webcast_language": "en",
                    }
                    api_headers = {
                        "User-Agent": self._desktop_ua,
                        "Referer": f"https://www.tiktok.com/@{unique_id}",
                        "Accept": "application/json, text/plain, */*",
                    }

                    try:
                        resp = await client.get(
                            "https://www.tiktok.com/api/creator/item_list/",
                            params=query,
                            headers=api_headers,
                        )
                        res_json = resp.json()
                    except Exception as e:
                        logger.warning(f"Lỗi khi gọi item_list page {page_count}: {e}")
                        break

                    status_code = res_json.get("statusCode", 0)
                    if status_code != 0:
                        logger.warning(f"TikTok item_list trả về mã lỗi: {status_code} - {res_json.get('status_msg')}")
                        break

                    items = res_json.get("itemList", [])
                    has_more = bool(res_json.get("hasMorePrevious", False))

                    if not items:
                        break

                    for it in items:
                        vid = it.get("id")
                        if not vid or vid in seen_ids:
                            continue
                        seen_ids.add(vid)

                        video_meta = it.get("video", {})
                        stats = it.get("stats", {})
                        
                        cover = (
                            video_meta.get("cover")
                            or video_meta.get("originCover")
                            or video_meta.get("dynamicCover")
                        )

                        item_dict = {
                            "video_id": vid,
                            "url": f"https://www.tiktok.com/@{unique_id}/video/{vid}",
                            "title": it.get("desc") or "",
                            "cover_url": cover,
                            "duration_seconds": video_meta.get("duration"),
                            "created_at": it.get("createTime"),
                            "likes": stats.get("diggCount"),
                            "comments": stats.get("commentCount"),
                            "shares": stats.get("shareCount"),
                            "views": stats.get("playCount"),
                            "bookmarks": stats.get("collectCount"),
                        }
                        videos_list.append(item_dict)
                        if len(videos_list) >= max_count:
                            break

                    last_item = items[-1]
                    create_time = int(last_item.get("createTime", 0)) * 1000
                    if not create_time or create_time == cursor:
                        cursor = cursor - 7 * 86_400_000
                    else:
                        cursor = create_time
                    next_cursor = cursor

                    # Trì hoãn nhẹ tránh rate limit
                    await asyncio.sleep(0.3)

            return {
                "success": True,
                "platform": "tiktok",
                "username": unique_id,
                "author": profile,
                "total_collected": len(videos_list),
                "video_urls": [v["url"] for v in videos_list],
                "videos": videos_list,
                "has_more": has_more,
                "next_cursor": next_cursor,
                "error_code": None,
                "message": f"Đã thu thập thành công {len(videos_list)} video từ kênh @{unique_id}.",
            }

    async def get_single_video_info(self, video_url: str) -> Dict[str, Any]:
        """
        Trích xuất metadata chi tiết của một video TikTok đơn lẻ sử dụng yt-dlp.
        """
        if not is_safe_url(video_url):
            return {
                "success": False,
                "platform": "tiktok",
                "video": None,
                "error_code": "INVALID_OR_DISALLOWED_URL",
                "message": "URL video không hợp lệ hoặc bị chặn bởi chính sách SSRF.",
            }

        def _extract():
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(video_url, download=False)

        try:
            info = await asyncio.to_thread(_extract)
            if not info:
                return {
                    "success": False,
                    "platform": "tiktok",
                    "video": None,
                    "error_code": "VIDEO_NOT_FOUND",
                    "message": "Không tìm thấy thông tin video TikTok này.",
                }

            vid = str(info.get("id") or "")
            thumbnails = info.get("thumbnails", [])
            cover_url = thumbnails[-1].get("url") if thumbnails else info.get("thumbnail")

            video_item = {
                "video_id": vid,
                "url": info.get("webpage_url") or video_url,
                "title": info.get("title") or info.get("description"),
                "cover_url": cover_url,
                "duration_seconds": info.get("duration"),
                "created_at": info.get("timestamp"),
                "likes": info.get("like_count"),
                "comments": info.get("comment_count"),
                "shares": info.get("repost_count"),
                "views": info.get("view_count"),
                "bookmarks": info.get("save_count"),
            }

            return {
                "success": True,
                "platform": "tiktok",
                "video": video_item,
                "error_code": None,
                "message": "Lấy thông tin video thành công.",
            }
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất video {video_url}: {e}")
            return {
                "success": False,
                "platform": "tiktok",
                "video": None,
                "error_code": "EXTRACTION_ERROR",
                "message": f"Không thể lấy thông tin video: {str(e)}",
            }
