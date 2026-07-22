import re
import math
import logging
import requests
from typing import Dict, Any, List, Optional
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Broad regex pattern matching standard, share, reel, and mobile Facebook URLs
FB_URL_REGEX = re.compile(
    r'^https?://(?:www\.|web\.|m\.|mobile\.|fb\.)?(?:facebook\.com|fb\.watch|fb\.gg)/.+$',
    re.IGNORECASE
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def is_valid_facebook_url(url: str) -> bool:
    """Validates Facebook video URL format."""
    if not url or not isinstance(url, str):
        return False
    return bool(FB_URL_REGEX.match(url.strip()))

def resolve_redirect_url(url: str) -> str:
    """
    Resolves shortened or share links like /share/r/ or fb.watch/ to their direct canonical URL.
    """
    try:
        # Check if URL is a share redirect link
        if '/share/' in url or 'fb.watch' in url:
            logger.info(f"Resolving redirect link: {url}")
            res = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=6)
            if res.url and res.url != url:
                logger.info(f"Resolved URL to: {res.url}")
                return res.url
    except Exception as err:
        logger.warning(f"HEAD request failed during URL resolution: {err}")
        try:
            res = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=6, stream=True)
            if res.url:
                return res.url
        except Exception as get_err:
            logger.warning(f"GET request failed during URL resolution: {get_err}")
    return url

def format_bytes(size_in_bytes: Optional[int]) -> str:
    """Converts raw byte count into human-readable string."""
    if not size_in_bytes or size_in_bytes <= 0:
        return "Unknown Size"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_duration(seconds: Optional[int]) -> str:
    """Formats duration seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds <= 0:
        return "Live / Standard"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def extract_facebook_info(url: str) -> Dict[str, Any]:
    """
    Extracts video metadata and format quality options using yt-dlp.
    Returns clean dictionary data or error dict.
    """
    raw_url = url.strip()

    if not is_valid_facebook_url(raw_url):
        return {
            "success": False,
            "error": "Invalid Facebook URL format. Please paste a valid Facebook video, reel, or share link."
        }

    # Resolve share links (/share/r/, /share/v/, fb.watch)
    resolved_url = resolve_redirect_url(raw_url)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best',
        'socket_timeout': 12,
        'user_agent': HEADERS['User-Agent'],
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting with yt-dlp: {resolved_url}")
            info = ydl.extract_info(resolved_url, download=False)

            if not info:
                return {
                    "success": False,
                    "error": "Unable to extract video details. Video may be private, restricted, or removed."
                }

            raw_formats = info.get('formats', [])
            available_formats: List[Dict[str, Any]] = []
            seen_qualities = set()

            for fmt in raw_formats:
                dl_url = fmt.get('url')
                if not dl_url:
                    continue

                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                height = fmt.get('height') or 0
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                ext = fmt.get('ext', 'mp4')

                # Identify target height quality
                quality_label = ""
                if height >= 1080:
                    quality_label = "1080P"
                elif height >= 720:
                    quality_label = "720P"
                elif height >= 480:
                    quality_label = "480P"
                elif height >= 360:
                    quality_label = "360P"
                elif height > 0:
                    quality_label = f"{height}P"
                elif vcodec == 'none' and acodec != 'none':
                    quality_label = "Audio Only"

                if not quality_label:
                    continue

                fmt_key = f"{quality_label}_{ext}"
                if fmt_key in seen_qualities:
                    continue

                seen_qualities.add(fmt_key)
                is_audio = (quality_label == "Audio Only")
                
                label_text = "MP3 Audio (128kbps)" if is_audio else f"MP4 Video ({quality_label} HD)" if height >= 720 else f"MP4 Video ({quality_label} SD)"

                available_formats.append({
                    "quality": quality_label,
                    "label": label_text,
                    "ext": "mp3" if is_audio else ext,
                    "url": dl_url,
                    "filesize": format_bytes(filesize),
                    "is_audio": is_audio,
                    "has_video": vcodec != 'none'
                })

            # Sort qualities high to low
            order = {"1080P": 1, "720P": 2, "480P": 3, "360P": 4, "Audio Only": 5}
            available_formats.sort(key=lambda x: order.get(x["quality"], 99))

            # Fallback if no specific format list was extracted
            if not available_formats and info.get('url'):
                available_formats.append({
                    "quality": "720P",
                    "label": "MP4 Video (Standard Quality)",
                    "ext": info.get('ext', 'mp4'),
                    "url": info.get('url'),
                    "filesize": format_bytes(info.get('filesize')),
                    "is_audio": False,
                    "has_video": True
                })

            if not available_formats:
                return {
                    "success": False,
                    "error": "No downloadable video streams were found for this Facebook post."
                }

            return {
                "success": True,
                "data": {
                    "title": info.get('title') or info.get('description') or "Facebook Video",
                    "thumbnail": info.get('thumbnail') or "https://via.placeholder.com/640x360?text=Facebook+Video",
                    "duration": format_duration(info.get('duration')),
                    "original_url": raw_url,
                    "uploader": info.get('uploader') or "Facebook Creator",
                    "formats": available_formats
                }
            }

    except yt_dlp.utils.DownloadError as de:
        logger.error(f"yt-dlp DownloadError: {str(de)}")
        return {
            "success": False,
            "error": "Failed to fetch video. Please check if the post is public and accessible."
        }
    except Exception as e:
        logger.error(f"Extraction Exception: {str(e)}")
        return {
            "success": False,
            "error": "An error occurred while parsing video data from Facebook."
        }
