import re
import math
import logging
from typing import Dict, Any, List, Optional
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Facebook URL Validation Regex Pattern
FB_URL_REGEX = re.compile(
    r'^https?://(?:www\.|web\.|m\.|mobile\.|fb\.)?(?:facebook\.com|fb\.watch|fb\.gg)/.+$',
    re.IGNORECASE
)

def is_valid_facebook_url(url: str) -> bool:
    """Validates whether a given string is a valid Facebook video URL."""
    if not url or not isinstance(url, str):
        return False
    return bool(FB_URL_REGEX.match(url.strip()))

def format_bytes(size_in_bytes: Optional[int]) -> str:
    """Converts bytes to human-readable string format."""
    if not size_in_bytes or size_in_bytes <= 0:
        return "Unknown Size"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_duration(seconds: Optional[int]) -> str:
    """Converts duration in seconds to HH:MM:SS or MM:SS format."""
    if not seconds or seconds <= 0:
        return "Live / Unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def extract_facebook_info(url: str) -> Dict[str, Any]:
    """
    Extracts Facebook video metadata and available qualities using yt-dlp.
    Returns a clean structured dictionary.
    """
    cleaned_url = url.strip()
    
    if not is_valid_facebook_url(cleaned_url):
        return {
            "success": False,
            "error": "Invalid Facebook URL format. Please provide a valid Facebook video or reel link."
        }

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'extract_flat': False,
        'skip_download': True,
        'socket_timeout': 15,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting info for URL: {cleaned_url}")
            info = ydl.extract_info(cleaned_url, download=False)

            if not info:
                return {
                    "success": False,
                    "error": "Unable to extract video details. Video might be private or deleted."
                }

            # Process formats
            raw_formats = info.get('formats', [])
            available_formats: List[Dict[str, Any]] = []
            seen_qualities = set()

            # Iterate through formats to filter out clean video and audio options
            for fmt in raw_formats:
                download_url = fmt.get('url')
                if not download_url:
                    continue

                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                height = fmt.get('height') or 0
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                ext = fmt.get('ext', 'mp4')

                # Identify quality target
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

                format_key = f"{quality_label}_{ext}"
                if format_key in seen_qualities:
                    continue

                seen_qualities.add(format_key)

                is_audio = (quality_label == "Audio Only")
                display_name = f"MP3 Audio (128kbps)" if is_audio else f"MP4 - {quality_label} HD" if height >= 720 else f"MP4 - {quality_label} SD"

                available_formats.append({
                    "quality": quality_label,
                    "label": display_name,
                    "ext": "mp3" if is_audio else ext,
                    "url": download_url,
                    "filesize": format_bytes(filesize),
                    "is_audio": is_audio,
                    "has_video": vcodec != 'none'
                })

            # Sort formats: HD first, then SD, then Audio
            quality_order = {"1080P": 1, "720P": 2, "480P": 3, "360P": 4, "Audio Only": 5}
            available_formats.sort(key=lambda x: quality_order.get(x["quality"], 99))

            # Fallback if no specific formats list was parsed properly
            if not available_formats and info.get('url'):
                available_formats.append({
                    "quality": "720P",
                    "label": "MP4 - Video (HD/SD)",
                    "ext": info.get('ext', 'mp4'),
                    "url": info.get('url'),
                    "filesize": format_bytes(info.get('filesize')),
                    "is_audio": False,
                    "has_video": True
                })

            if not available_formats:
                return {
                    "success": False,
                    "error": "No downloadable video streams found for this link."
                }

            # Return normalized clean JSON response
            return {
                "success": True,
                "data": {
                    "title": info.get('title') or info.get('description') or "Facebook Video",
                    "thumbnail": info.get('thumbnail') or "https://via.placeholder.com/640x360?text=Facebook+Video",
                    "duration": format_duration(info.get('duration')),
                    "original_url": cleaned_url,
                    "uploader": info.get('uploader') or "Facebook Creator",
                    "formats": available_formats
                }
            }

    except yt_dlp.utils.DownloadError as de:
        logger.error(f"yt-dlp Download Error: {str(de)}")
        return {
            "success": False,
            "error": "Failed to fetch video. Ensure the video is public and accessible."
        }
    except Exception as e:
        logger.error(f"Unhandled Extraction Error: {str(e)}")
        return {
            "success": False,
            "error": "An unexpected error occurred while parsing the video URL."
        }
