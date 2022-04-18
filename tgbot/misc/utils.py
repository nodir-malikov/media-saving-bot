import os
import base64
import zlib
import validators

from enum import Enum

from loguru import logger


UNIVERSAL_UA = \
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us; Silk/1.0.146.3-Gen4_12000410) ' \
    'AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16 Silk-Accelerated=true'


class SPP_SM_BASE_URLS(Enum):
    INSTAGRAM = "instagram.com"
    YOUTUBE = "youtube.com"
    YOUTUBE_SHORT = "youtu.be"
    # TIKTOK = "tiktok.com"


async def clean_url(url: str) -> str:
    """Clean url from "http://", "https://", "www.", last "/" and params"""
    url = url.replace("http://", "")
    url = url.replace("https://", "")
    url = url.replace("www.", "")
    if url[-1] == "/":
        url = url[:-1]
    url = url.split("?")[0]
    return url


async def is_url(url: str) -> bool:
    """Check if url is valid"""
    try:
        return validators.url(url)
    except Exception as e:
        logger.error(f"Error while checking url {url}:\n{e}")
        return False


async def is_allowed_social_media(url: str) -> str or None:
    """Check if url is from allowed social media"""
    url = await clean_url(url)
    for sm in SPP_SM_BASE_URLS:
        if sm.value in url:
            return sm.value
    return False


async def humanbytes(num, suffix='B'):
    if num is None:
        num = 0
    else:
        num = int(num)

    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


async def show_format_sizes(video_formats: list) -> str:
    """Show video formats sizes"""
    sizes = []
    for format in video_formats:
        height = format['height']
        filesize = format['filesize']
        # add ✅ before strings
        # if filesize is greater than 2GB add 🛑 before strings
        if filesize > 2147483648:  # 2GB
            sizes.append(f"<code>🛑\t{height}p:\t{await humanbytes(filesize)}</code>")
        else:
            sizes.append(f"<code>✅\t{height}p:\t{await humanbytes(filesize)}</code>")
    return "\n".join(sizes)


async def compress_string(string: str) -> str:
    """Compress string"""
    return base64.b64encode(zlib.compress(string.encode())).decode()


async def decompress_string(string: str) -> str:
    """Decompress string"""
    return zlib.decompress(base64.b64decode(string)).decode()


async def delete_file(filepath: str) -> bool:
    """
    Delete thumbnail from filepath
    """
    try:
        os.remove(filepath)
        return True
    except Exception as e:
        logger.error(e)
        return False
