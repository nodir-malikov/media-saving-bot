import os
import re
import asyncio
import datetime
from textwrap import indent
import aiohttp
import jmespath
import json

from enum import Enum

from http.cookies import SimpleCookie

from loguru import logger

from tgbot.misc.utils import UNIVERSAL_UA

INSTA_HEADERS = {
    "User-Agent": UNIVERSAL_UA,
}


class CODES(Enum):
    DOWNLOADED = 1
    NOT_FOUND = 0
    COULD_NOT_LOGIN = -10
    COULD_NOT_DOWNLOAD = -20
    ERROR = -100


class Instagram():
    """Instagram API wrapper"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.directory = os.path.join(os.getcwd(), "media", "instagram")
        self.login_attempts = 0

    async def login(self):
        """Login to Instagram, cache and return session cookies"""

        time = str(int(datetime.datetime.now().timestamp()))
        enc_password = f"#PWD_INSTAGRAM_BROWSER:0:{time}:{self.password}"

        try:
            async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:

                # # Log out
                # async with session.post('https://www.instagram.com/accounts/logout/ajax/', headers=INSTA_HEADERS) as resp:
                #     logger.debug(f"Logged out: {resp.status}")

                # Get CSRF token
                async with session.get("https://www.instagram.com/", headers=INSTA_HEADERS) as resp:
                    cookies = session.cookie_jar.filter_cookies(
                        "https://www.instagram.com")
                    csrftoken = cookies["csrftoken"].value
                    # set a cookie that signals Instagram the "Accept cookie" banner was closed
                    ig_cb = SimpleCookie({"ig_cb": "2"})
                    session.cookie_jar.update_cookies(ig_cb)

                # Login
                async with session.post(
                    "https://www.instagram.com/accounts/login/ajax/",
                    data={
                        "username": self.username,
                        "enc_password": enc_password,
                    },
                    headers={
                        "Referer": "https://www.instagram.com/",
                        "User-Agent": INSTA_HEADERS["User-Agent"],
                        "X-CSRFToken": csrftoken,
                    },
                ) as resp:
                    resp_json = json.loads(await resp.text())
                    logger.debug(f"Login response: {resp_json}")
                    if resp_json["authenticated"] == True:
                        logger.success("Logged in successfully")
                        return session.cookie_jar
                    else:
                        logger.error(f"Login failed")
                        return None
        except Exception as e:
            logger.error(f"Error while logging in:\n{e}")
            raise e

    async def try_login(self, new_cookie=False):
        """Try to login to Instagram, with saved cookies or login if otherwise"""

        if os.path.exists(os.path.join(self.directory, "cookies.txt")):
            if new_cookie:
                os.remove(os.path.join(self.directory, "cookies.txt"))
            cookies = aiohttp.cookiejar.CookieJar(
                loop=asyncio.get_event_loop())
            with open(os.path.join(self.directory, "cookies.txt"), "r") as f:
                cookies.update_cookies(SimpleCookie(f.read()))
            logger.success("Login credentials (cookies) loaded from file")
            return cookies

        os.makedirs(self.directory, exist_ok=True, mode=0o755)

        cookies = await self.login()
        if cookies:
            with open(os.path.join(self.directory, "cookies.txt"), "w") as f:
                f.writelines(
                    [f'{cookie.output(header="").strip()}\n' for cookie in cookies]
                )
            return cookies
        else:
            return None

    async def download_post(self, url: str, new_cookie=False) -> int or tuple:
        """Download post (image or video)"""

        post_id = re.search(
            r"instagram.com/[-a-zA-Z0-9]+/([^/]*)",
            url
        ).group(1)
        # cookies = await self.try_login(new_cookie=new_cookie)

        # if cookies:
        if True:
            try:
                # async with aiohttp.ClientSession(cookie_jar=cookies) as session:
                async with aiohttp.ClientSession() as session:
                    # Get post data
                    async with session.get(url, headers=INSTA_HEADERS, params={"__a": "1"}) as resp:
                        logger.info(f"Post status: {resp.status}")
                        if resp.status == 404:
                            return CODES.NOT_FOUND.value
                        logger.debug(f"Post data: {await resp.text()}")
                        resp_json = json.loads(await resp.text())
                        logger.debug(
                            f"Post data:\n{json.dumps(resp_json, indent=4)}")
                        carousel_media = jmespath.search(
                            "items[0].carousel_media", resp_json)
                        if not carousel_media:
                            carousel_media = jmespath.search(
                                "graphql.shortcode_media.edge_sidecar_to_children",
                                resp_json
                            )
                        image_url = jmespath.search(
                            "items[0].image_versions2.candidates[0].url", resp_json
                        )
                        if not image_url:
                            image_url = jmespath.search(
                                "graphql.shortcode_media.display_url", resp_json
                            )
                        video_url = jmespath.search(
                            "items[0].video_versions[0].url", resp_json
                        )
                        if not video_url:
                            video_url = jmespath.search(
                                "graphql.shortcode_media.video_url", resp_json
                            )

                        if carousel_media:
                            if type(carousel_media) != list:
                                formula = \
                                    "edges[0:10].{image: node.display_url, video: node.video_url}"
                                carousel_media = jmespath.search(
                                    formula,
                                    carousel_media
                                )
                                # If has video pop image or pop video if video is None
                                for item in carousel_media:
                                    if item["video"]:
                                        del item["image"]
                                    if not item["video"]:
                                        del item["video"]

                            else:
                                formula = \
                                    "items[0].carousel_media[0:10]."\
                                    "{image: image_versions2.candidates[0].url, "\
                                    "video: video_versions[0].url}"
                                carousel_media = \
                                    jmespath.search(formula, resp_json)

                            carousel_save_path = ""
                            for index, media in enumerate(carousel_media):
                                if type(media) == dict:
                                    if not 'video' in media:  # image
                                        save_path = os.path.join(
                                            self.directory, "carousels", post_id)
                                        carousel_save_path = save_path
                                        os.makedirs(
                                            save_path, exist_ok=True, mode=0o755)
                                        save_path = os.path.join(
                                            save_path, f"{index}.jpg")

                                        image_url = media["image"]
                                        async with session.get(image_url, headers=INSTA_HEADERS) as image:
                                            if resp.status == 200:
                                                image_data = await image.read()
                                                with open(save_path, "wb") as f:
                                                    f.write(image_data)
                                                logger.success(
                                                    f"Saved image to {save_path}")
                                            else:
                                                logger.error(
                                                    f"Error while downloading carousel image: {resp.status}")
                                                return CODES.COULD_NOT_DOWNLOAD.value

                                    if 'video' in media:  # video
                                        save_path = os.path.join(
                                            self.directory, "carousels", post_id)
                                        os.makedirs(
                                            save_path, exist_ok=True, mode=0o755)
                                        save_path = os.path.join(
                                            save_path, f"{index}.mp4")

                                        video_url = media["video"]
                                        async with session.get(video_url, headers=INSTA_HEADERS) as video:
                                            if resp.status == 200:
                                                video_data = await video.read()
                                                with open(save_path, "wb") as f:
                                                    f.write(video_data)
                                                logger.success(
                                                    f"Saved video to {save_path}")
                                            else:
                                                logger.error(
                                                    f"Error while downloading carousel video: {resp.status}")
                                                return CODES.COULD_NOT_DOWNLOAD.value
                            return CODES.DOWNLOADED.value, \
                                {"path": carousel_save_path,
                                 "file_type": "carousel"}

                        if image_url and video_url:  # video
                            logger.info(f"Downloading video: {video_url}")

                            save_path = os.path.join(self.directory, "videos")
                            os.makedirs(save_path, exist_ok=True, mode=0o755)
                            save_path = os.path.join(
                                save_path, f"{post_id}.mp4")

                            async with session.get(video_url, headers=INSTA_HEADERS) as video:
                                if resp.status == 200:
                                    video_data = await video.read()
                                    with open(save_path, "wb") as f:
                                        f.write(video_data)
                                    logger.success(
                                        f"Saved video to {save_path}")
                                    return CODES.DOWNLOADED.value, \
                                        {"path": save_path,
                                         "file_type": "video"}
                                else:
                                    logger.error(
                                        f"Error while downloading image: {resp.status}")
                                    return CODES.COULD_NOT_DOWNLOAD.value

                        if image_url and not video_url:  # image
                            logger.info(f"Downloading image: {image_url}")

                            save_path = os.path.join(self.directory, "images")
                            os.makedirs(save_path, exist_ok=True, mode=0o755)
                            save_path = os.path.join(
                                save_path, f"{post_id}.jpg")

                            async with session.get(image_url, headers=INSTA_HEADERS) as image:
                                if resp.status == 200:
                                    image_data = await image.read()
                                    with open(save_path, "wb") as f:
                                        f.write(image_data)
                                    logger.success(
                                        f"Saved image to {save_path}")
                                    return CODES.DOWNLOADED.value, \
                                        {"path": save_path,
                                         "file_type": "image"}
                                else:
                                    logger.error(
                                        f"Error while downloading image: {resp.status}")
                                    return CODES.COULD_NOT_DOWNLOAD.value

            except Exception as e:
                logger.error(f"Error while downloading post: {e}")
                if "Cannot connect to host" in str(e):
                    logger.warning(
                        "Cannot connect to host. Please check your internet connection.")
                raise e

        logger.error("Could not login")
        # if self.login_attempts < 3:
        #     self.login_attempts += 1
        #     logger.warning(
        #         f"Retrying login attempt: {self.login_attempts}")
        #     await self.download_post(url, new_cookie=True)
        # self.login_attempts = 0
        return CODES.COULD_NOT_LOGIN.value

    async def download_story(self, url):
        """Downloads the story by given url"""
        pass
