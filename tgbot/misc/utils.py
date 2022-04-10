from enum import Enum
import validators
from loguru import logger


UNIVERSAL_UA = \
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us; Silk/1.0.146.3-Gen4_12000410) ' \
    'AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16 Silk-Accelerated=true'


class SPP_SM_BASE_URLS(Enum):
    INSTAGRAM = "instagram.com"
    # YOUTUBE = "youtube.com"
    # YOUTUBE_SHORT = "youtu.be"
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
