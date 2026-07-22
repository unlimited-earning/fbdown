import re
import math
import logging
import requests
from typing import Dict, Any, List, Optional
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FB_URL_REGEX = re.compile(
    r'^https?://(?:www\.|web\.|m\.|mobile\.|fb\.)?(?:facebook\.com|fb\.watch|fb\.gg)/.+$',
    re.IGNORECASE
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Mode': 'navigate',
}

def is_valid_facebook_url(url: str) -> bool:
    """Validates Facebook URL format."""
    if not url or not isinstance(url, str):
        return False
    return bool(FB_URL_REGEX.match(url.strip()))

def resolve_facebook_url(url: str) -> str:
    """Follows redirects for share/short links (/share/r/, fb.watch)."""
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        res = session.head(url, allow_redirects=True, timeout=8)
        if res.url and res.url != url:
            logger.info(f"Resolved URL [{url}] -> [{res.url}]")
            return res.url
    except Exception as err:
        logger.warning(f"HEAD request failed: {err}")
        try:
            res = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=8, stream=True)
            if res.url:
                return res.url
        except Exception as get_err:
            logger.warning(f"GET request failed: {get_err}")
    return url

def format_bytes(size_in_bytes: Optional[int]) -> str:
    """Human readable file size."""
    if not size_in_bytes or size_in_bytes <= 0:
        return "Standard Size"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_duration(seconds: Optional[int]) -> str:
    """Formats seconds into readable duration string."""
    if not seconds or seconds <= 0:
        return "Reel / Short Video"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def direct_html_fallback(url: str) -> Optional[Dict[str, Any]]:
    """Direct HTML Regex Fallback Engine if yt-dlp gets blocked by FB anti-bot."""
    try:
        logger.info("Attempting direct HTML scraper fallback...")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        html = resp.text

        # Extract HD and SD video links directly from page script
        hd_match = re.search(r'browser_native_hd_url":\s*"([^"]+)"', html) or re.search(r'playable_url_quality_hd":\s*"([^"]+)"', html)
        sd_match = re.search(r'browser_native_sd_url":\s*"([^"]+)"', html) or re.search(r'playable_url":\s*"([^"]+)"', html)
        title_match = re.search(r'<title>(.*?)</title>', html)

        hd_url = hd_match.group(1).replace(r'\/', '/') if hd_match else None
        sd_url = sd_match.group(1).replace(r'\/', '/') if sd_match else None
        title = title_match.group(1) if title_match else "Facebook Video"
        title = re.sub(r'\| Facebook$', '', title).strip()

        formats = []
        if hd_url:
            formats.append({
                "quality": "720P",
                "label": "MP4 Video (HD Quality)",
                "ext": "mp4",
                "url": hd_url,
                "filesize": "HD Stream",
                "is_audio": False,
                "has_video": True
            })
        if sd_url:
            formats.append({
                "quality": "360P",
                "label": "MP4 Video (SD Quality)",
                "ext": "mp4",
                "url": sd_url,
                "filesize": "SD Stream",
                "is_audio": False,
                "has_video": True
            })

        if formats:
            return {
                "success": True,
                "data": {
                    "title": title,
                    "thumbnail": "https://via.placeholder.com/640x360?text=Facebook+Video",
                    "duration": "Standard",
                    "original_url": url,
                    "uploader": "Facebook Post",
                    "formats": formats
                }
            }
    except Exception as e:
        logger.error(f"Fallback scraper failed: {e}")
    return None

def extract_facebook_info(url: str) -> Dict[str, Any]:
    """Main extractor routine."""
    raw_url = url.strip()

    if not is_valid_facebook_url(raw_url):
        return {
            "success": False,
            "error": "Invalid Facebook URL format. Please paste a valid Facebook video or reel link."
        }

    # Step 1: Resolve redirects (for /share/r/ links)
    target_url = resolve_facebook_url(raw_url)

    # Step 2: Extract with yt-dlp
    ydl_opts = {
        'q
