import re
import math
import logging
import requests
from typing import Dict, Any, List, Optional
import yt_dlp

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Downloader")

# Regex pattern for validating Facebook URLs (videos, watch, reels, share links)
FB_URL_REGEX = re.compile(
    r'^https?://(?:www\.|web\.|m\.|mobile\.|fb\.)?(?:facebook\.com|fb\.watch|fb\.gg)/.+$',
    re.IGNORECASE
)

# Standard HTTP headers for resolving redirect URLs
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def is_valid_facebook_url(url: str) -> bool:
    """Validates whether the provided string matches a Facebook video URL pattern."""
    if not url or not isinstance(url, str):
        return False
    return bool(FB_URL_REGEX.match(url.strip()))

def resolve_redirect_url(url: str) -> str:
    """
    Resolves shortened/share links (e.g. /share/r/, fb.watch) to canonical URLs.
    Prevents extraction failures from Facebook share redirects.
    """
    try:
        clean_url = url.strip()
        if '/share/' in clean_url or 'fb.watch' in clean_url:
            logger.info(f"Resolving share redirect URL: {clean_url}")
            response = requests.head(clean_url, headers=REQUEST_HEADERS, allow_redirects=True, timeout=6)
            if response.url and response.url != clean_url:
                logger.info(f"Successfully resolved URL to: {response.url}")
                return response.url
    except Exception as e:
        logger.warning(f"Failed HEAD redirect resolution: {str(e)}")
        try:
            response = requests.get(clean_url, headers=REQUEST_HEADERS, allow_redirects=True, timeout=6, stream=True)
            if response.url:
                return response.url
        except Exception as inner_e:
            logger.warning(f"Failed GET redirect resolution: {str(inner_e)}")
    return url

def format_bytes(size_bytes: Optional[int]) -> str:
    """Converts bytes to a human-readable size string."""
    if not size_bytes or size_bytes <= 0:
        return "Unknown Size"
    units = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {units[i]}"

def format_duration(seconds: Optional[int]) -> str:
    """Converts duration in seconds into HH:MM:SS or MM:SS format."""
    if not seconds or seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def get_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts Facebook video metadata and quality streams using yt-dlp.
    Guarantees clean JSON output structure and complete error handling.
    """
    try:
        raw_url = str(url).strip()

        # Step 1: Validate URL
        if not is_valid_facebook_url(raw_url):
            return {
                "success": False,
                "message": "Invalid Facebook URL format. Please provide a valid Facebook video or reel link."
            }

        # Step 2: Resolve redirects
        resolved_url = resolve_redirect_url(raw_url)

        # Step 3: Configure yt-dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'format': 'best',
            'socket_timeout': 15,
            'user_agent': REQUEST_HEADERS['User-Agent'],
            'nocheckcertificate': True,
        }

        # Step 4: Extract Metadata
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting video details for: {resolved_url}")
            info = ydl.extract_info(resolved_url, download=False)

            if not info:
                return {
                    "success": False,
                    "message": "Could not retrieve video details. The video may be private or deleted."
                }

            raw_formats = info.get('formats', [])
            available_formats: List[Dict[str, Any]] = []
            seen_qualities = set()

            for fmt in raw_formats:
                download_url = fmt.get('url')
                if not download_url:
                    continue

                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                height = fmt.get('height') or 0
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                ext = fmt.get('ext', 'mp4')

                # Classify Quality Label
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

                unique_key = f"{quality_label}_{ext}"
                if unique_key in seen_qualities:
                    continue

                seen_qualities.add(unique_key)
                is_audio = (quality_label == "Audio Only")

                display_label = "MP3 Audio (128kbps)" if is_audio else f"MP4 ({quality_label} HD)" if height >= 720 else f"MP4 ({quality_label} SD)"

                available_formats.append({
                    "quality": quality_label,
                    "label": display_label,
                    "ext": "mp3" if is_audio else ext,
                    "url": download_url,
                    "filesize": format_bytes(filesize),
                    "is_audio": is_audio
                })

            # Sort qualities: 1080p -> 720p -> 480p -> 360p -> Audio
            sort_order = {"1080P": 1, "720P": 2, "480P": 3, "360P": 4, "Audio Only": 5}
            available_formats.sort(key=lambda item: sort_order.get(item["quality"], 99))

            # Fallback if specific quality array is empty
            if not available_formats and info.get('url'):
                available_formats.append({
                    "quality": "720P",
                    "label": "MP4 (Standard Video)",
                    "ext": info.get('ext', 'mp4'),
                    "url": info.get('url'),
                    "filesize": format_bytes(info.get('filesize')),
                    "is_audio": False
                })

            if not available_formats:
                return {
                    "success": False,
                    "message": "No downloadable video streams found for this URL."
                }

            title = info.get('title') or info.get('description') or "Facebook Video"
            thumbnail = info.get('thumbnail') or "https://via.placeholder.com/640x360?text=Facebook+Video"
            duration = format_duration(info.get('duration'))
            uploader = info.get('uploader') or "Facebook User"

            return {
                "success": True,
                "title": title.strip(),
                "thumbnail": thumbnail,
                "duration": duration,
                "uploader": uploader,
                "original_url": raw_url,
                "formats": available_formats
            }

    except yt_dlp.utils.DownloadError as de:
        logger.error(f"yt-dlp error: {str(de)}")
        return {
            "success": False,
            "message": "Failed to fetch video. Ensure the video is public and accessible."
        }
    except Exception as e:
        logger.error(f"Unhandled Extraction Error: {str(e)}")
        return {
            "success": False,
            "message": "An unexpected error occurred while processing the video URL."
        }
