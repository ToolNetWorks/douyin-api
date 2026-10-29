import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext
from playwright_stealth import Stealth
from f2.apps.douyin.utils import TokenManager

from app.core.config import settings

logger = logging.getLogger("douyin_scraper")
logger.setLevel(logging.INFO)

def get_chromium_path() -> Optional[str]:
    """Finds Chromium executable or returns None to use Playwright's default"""
    if settings.CHROME_PATH and Path(settings.CHROME_PATH).exists():
        return settings.CHROME_PATH
    for p in ["/snap/bin/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
        if Path(p).exists():
            return p
    return None

def get_system_cookie() -> str:
    """Reads default Douyin cookie string from env var or file search paths"""
    if settings.COOKIE_STR:
        return settings.COOKIE_STR
    
    for path in settings.cookie_search_paths:
        if path.name == "cookie.txt" and path.exists():
            try:
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except Exception:
                pass
        elif path.name == ".env" and path.exists():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("DOUYIN_COOKIE="):
                        val = line.split("=", 1)[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if val:
                            return val
            except Exception:
                pass

    return ""

def get_structured_cookies_from_files() -> List[Dict[str, Any]]:
    """Checks for DOUYIN_COOKIES_JSON in env or cookies.json in search paths and parses cookie dicts"""
    raw_env_json = os.environ.get("DOUYIN_COOKIES_JSON", "").strip()
    if raw_env_json:
        try:
            parsed = json.loads(raw_env_json)
            if isinstance(parsed, dict) and "cookies" in parsed:
                parsed = parsed["cookies"]
            if isinstance(parsed, list):
                cookie_list = []
                for c in parsed:
                    if c.get("name") and c.get("value") is not None:
                        cookie_list.append({
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".douyin.com"),
                            "path": c.get("path", "/"),
                        })
                if cookie_list:
                    return cookie_list
        except Exception as e:
            logger.warning(f"Could not load cookies from DOUYIN_COOKIES_JSON: {e}")

    for path in settings.cookie_search_paths:
        if path.name == "cookies.json" and path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw_cookies = json.load(f)
                cookie_list = []
                for c in raw_cookies:
                    if c.get("name") and c.get("value") is not None:
                        cookie_list.append({
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".douyin.com"),
                            "path": c.get("path", "/"),
                        })
                if cookie_list:
                    return cookie_list
            except Exception as e:
                logger.warning(f"Could not load cookies from {path}: {e}")
    return []

def extract_raw_url(text: str) -> Optional[str]:
    """Extract http/https URL from user text (e.g. share texts)"""
    if not text:
        return None
    match = re.search(r"https?://[^\s\"'<>]+", text)
    if match:
        return match.group(0).rstrip(".,;!?")
    clean = text.strip()
    if any(clean.startswith(prefix) for prefix in ["v.douyin.com", "www.douyin.com", "douyin.com", "iesdouyin.com"]):
        return f"https://{clean}"
    return clean

async def resolve_douyin_url(input_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolves input text/URL to (canonical_user_url, sec_user_id).
    Handles short links (v.douyin.com), web links, and share snippets.
    """
    raw_url = extract_raw_url(input_text)
    if not raw_url:
        return None, None
        
    # Check if raw input is already just a sec_user_id (MS4wLjABAAAA...)
    if raw_url.startswith("MS4wLjABAAAA"):
        return f"https://www.douyin.com/user/{raw_url}", raw_url

    # Check if user URL is directly formatted
    match = re.search(r"user/([a-zA-Z0-9_\-]+)", raw_url)
    if match:
        sec_id = match.group(1)
        return f"https://www.douyin.com/user/{sec_id}", sec_id

    # If it's a short link or redirect link
    try:
        req_url = raw_url
        if not req_url.startswith("http://") and not req_url.startswith("https://"):
            req_url = f"https://{req_url}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            }
            resp = await client.get(req_url, headers=headers)
            final_url = str(resp.url)
            
            # Check user pattern
            match = re.search(r"user/([a-zA-Z0-9_\-]+)", final_url)
            if match:
                sec_id = match.group(1)
                return f"https://www.douyin.com/user/{sec_id}", sec_id
                
            # Check query param sec_uid
            match_sec = re.search(r"sec_uid=([a-zA-Z0-9_\-]+)", final_url)
            if match_sec:
                sec_id = match_sec.group(1)
                return f"https://www.douyin.com/user/{sec_id}", sec_id
                
            # Check modal_id or video redirect
            match_vid = re.search(r"modal_id=([0-9]+)", final_url)
            if match_vid:
                text = resp.text
                match_html = re.search(r"\"sec_uid\":\"([^\"]+)\"", text)
                if match_html:
                    sec_id = match_html.group(1)
                    return f"https://www.douyin.com/user/{sec_id}", sec_id

    except Exception as e:
        logger.error(f"Error resolving URL redirect: {e}")

    return None, None


class DouyinScraper:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CRAWLS)

    async def _get_browser(self):
        if not self.browser or not self.playwright or not self.browser.is_connected():
            if self.browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass
                self.browser = None
            if not self.playwright:
                self.playwright = await async_playwright().start()
            launch_kwargs = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--mute-audio",
                    "--no-zygote",
                    "--disable-extensions",
                    "--disable-component-update",
                    "--disable-background-networking",
                    "--disable-features=Translate,BackForwardCache,MediaRouter,OptimizationHints,AudioServiceOutOfProcess",
                    "--js-flags=--max-old-space-size=256",
                    "--disable-blink-features=AutomationControlled",
                ],
            }
            chrome_path = get_chromium_path()
            if chrome_path:
                launch_kwargs["executable_path"] = chrome_path
                logger.info(f"Using Chromium binary at: {chrome_path}")
            else:
                logger.info("Using Playwright bundled Chromium")

            self.browser = await self.playwright.chromium.launch(**launch_kwargs)
        return self.browser

    async def get_channel_videos(
        self,
        channel_url_or_sec_id: str,
        max_count: int = 50,
        custom_cookie: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrapes video URLs and details from a Douyin channel link.
        """
        canonical_url, sec_user_id = await resolve_douyin_url(channel_url_or_sec_id)
        if not sec_user_id:
            raise ValueError(
                f"Không thể phân tích hoặc tìm thấy ID kênh Douyin hợp lệ từ link: {channel_url_or_sec_id}"
            )

        async with self._semaphore:
            browser = await self._get_browser()
            
            context: BrowserContext = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            
            # Prepare pre-seeded cookies
            cookie_list: List[Dict[str, Any]] = []
            
            # 1. Structured cookies.json if no custom cookie passed
            if not custom_cookie:
                cookie_list = get_structured_cookies_from_files()

            # 2. String cookies (custom_cookie, cookie.txt, or .env)
            if not cookie_list:
                effective_cookie = custom_cookie or get_system_cookie()
                if effective_cookie:
                    www_cookie_names = {
                        "web_sign_token", "s_v_web_id", "dy_swidth", "dy_sheight",
                        "bd_ticket_guard_web_domain", "__ac_nonce", "__ac_signature",
                        "douyin.com", "device_web_cpu_core", "device_web_memory_size",
                        "bd_ticket_guard_core_version", "bd-web-sign-page-guard"
                    }
                    for part in effective_cookie.split(";"):
                        if "=" in part:
                            name, val = part.strip().split("=", 1)
                            clean_name = name.strip()
                            domain = "www.douyin.com" if clean_name in www_cookie_names else ".douyin.com"
                            cookie_list.append({
                                "name": clean_name,
                                "value": val.strip(),
                                "domain": domain,
                                "path": "/",
                            })

            # Always ensure basic ByteDance tokens exist if not present in cookies
            existing_cookie_names = {c["name"] for c in cookie_list}
            try:
                if "ttwid" not in existing_cookie_names:
                    ttwid = TokenManager.gen_ttwid()
                    cookie_list.append({"name": "ttwid", "value": ttwid, "domain": ".douyin.com", "path": "/"})
                if "msToken" not in existing_cookie_names:
                    ms_token = TokenManager.gen_real_msToken()
                    cookie_list.append({"name": "msToken", "value": ms_token, "domain": ".douyin.com", "path": "/"})
                if "enter_pc_once" not in existing_cookie_names:
                    cookie_list.append({"name": "enter_pc_once", "value": "1", "domain": ".douyin.com", "path": "/"})
            except Exception as e:
                logger.warning(f"Could not pre-generate tokens: {e}")

            if cookie_list:
                await context.add_cookies(cookie_list)

            page = await context.new_page()

            # Abort heavy media streaming (mp4/flv/m3u8) to save RAM and avoid OOM
            async def intercept_route(route):
                if route.request.resource_type in ["media"]:
                    await route.abort()
                else:
                    await route.continue_()
            await page.route("**/*", intercept_route)

            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            videos_dict: Dict[str, Dict[str, Any]] = {}
            author_info: Dict[str, Any] = {"sec_uid": sec_user_id}
            has_more = True
            post_event = asyncio.Event()

            async def on_response(res):
                nonlocal has_more
                if "aweme/post" in res.url:
                    logger.info(f"aweme/post response intercepted: status={res.status}")
                    try:
                        data = await res.json()
                        has_more = bool(data.get("has_more", 0))
                        awemes = data.get("aweme_list", [])
                        logger.info(f"awemes parsed: count={len(awemes)}, has_more={has_more}")
                        for item in awemes:
                            aid = item.get("aweme_id")
                            if not aid or aid in videos_dict:
                                continue

                            # Save author info if not yet populated
                            author = item.get("author", {})
                            if author and "nickname" not in author_info:
                                author_info["nickname"] = author.get("nickname")
                                author_info["uid"] = author.get("uid")
                                author_info["avatar"] = (
                                    author.get("avatar_thumb", {}).get("url_list", [""])[0]
                                )
                                author_info["signature"] = author.get("signature")

                            video_data = item.get("video", {})
                            play_addr_list = video_data.get("play_addr", {}).get("url_list", [])
                            cover_list = video_data.get("cover", {}).get("url_list", [])

                            play_url = play_addr_list[0] if play_addr_list else None
                            cover_url = cover_list[0] if cover_list else None
                            
                            stats = item.get("statistics", {})

                            videos_dict[aid] = {
                                "id": aid,
                                "url": f"https://www.douyin.com/video/{aid}",
                                "title": item.get("desc") or "",
                                "play_url": play_url,
                                "cover_url": cover_url,
                                "duration_seconds": round(video_data.get("duration", 0) / 1000, 2),
                                "width": video_data.get("width"),
                                "height": video_data.get("height"),
                                "created_time": item.get("create_time"),
                                "stats": {
                                    "likes": stats.get("digg_count", 0),
                                    "comments": stats.get("comment_count", 0),
                                    "shares": stats.get("share_count", 0),
                                    "bookmarks": stats.get("collect_count", 0),
                                },
                            }
                    except Exception as e:
                        logger.error(f"Failed to parse aweme/post json: {e}")
                    finally:
                        post_event.set()

            page.on("response", on_response)

            try:
                # Navigate directly to user profile
                logger.info(f"Navigating to {canonical_url}...")
                await page.goto(canonical_url, wait_until="commit", timeout=settings.PAGE_TIMEOUT_MS)
                await asyncio.sleep(4.0)

                # Trigger post request by mouse wheel
                await page.mouse.move(640, 400)
                await page.mouse.wheel(0, 2500)
                try:
                    await asyncio.wait_for(post_event.wait(), timeout=9.0)
                except asyncio.TimeoutError:
                    pass

                # Extract author nickname/works count from page DOM if not yet populated
                if "nickname" not in author_info:
                    try:
                        dom_info = await page.evaluate('''() => {
                            const detail = document.querySelector('[data-e2e="user-detail"]');
                            const count = document.querySelector('[data-e2e="user-tab-count"]');
                            return {
                                text: detail ? detail.innerText : '',
                                total_works: count ? count.innerText : ''
                            };
                        }''')
                        if dom_info.get("text"):
                            lines = dom_info["text"].split("\n")
                            if lines:
                                author_info["nickname"] = lines[0].strip()
                        if dom_info.get("total_works"):
                            author_info["total_works"] = dom_info["total_works"]
                    except Exception as e:
                        logger.debug(f"Could not extract DOM details: {e}")

                # Scroll to collect more videos if requested and needed
                scroll_count = 0
                consecutive_misses = 0
                max_scrolls = max(10, (max_count // 15) + 5)
                start_loop_time = asyncio.get_event_loop().time()
                while len(videos_dict) < max_count and scroll_count < max_scrolls and has_more:
                    if asyncio.get_event_loop().time() - start_loop_time > 40.0:
                        logger.info("Scrape loop safety timeout reached (40s). Returning collected videos.")
                        break

                    prev_count = len(videos_dict)
                    post_event.clear()
                    scroll_count += 1
                    
                    # Scroll via both mouse wheel and container.scrollTop
                    await page.mouse.wheel(0, 3500)
                    try:
                        await page.evaluate('''() => {
                            const sc = document.querySelector('.route-scroll-container') || document.querySelector('[class*="route-scroll"]');
                            if (sc) sc.scrollTop = sc.scrollHeight;
                        }''')
                    except Exception as e:
                        logger.debug(f"Scroll evaluate error: {e}")
                    
                    try:
                        await asyncio.wait_for(post_event.wait(), timeout=7.0)
                    except asyncio.TimeoutError:
                        consecutive_misses += 1
                        if consecutive_misses >= 2:
                            break
                        continue

                    if len(videos_dict) == prev_count:
                        consecutive_misses += 1
                        if consecutive_misses >= 2:
                            break
                    else:
                        consecutive_misses = 0

                    await asyncio.sleep(1.2)

            finally:
                await context.close()

            video_list = list(videos_dict.values())
            if max_count > 0:
                video_list = video_list[:max_count]

            return {
                "sec_user_id": sec_user_id,
                "canonical_url": canonical_url,
                "author": author_info,
                "total_collected": len(video_list),
                "has_more": has_more,
                "video_urls": [v["url"] for v in video_list],
                "videos": video_list,
            }

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
