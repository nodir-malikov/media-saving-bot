import os

import jmespath

from aiofiles import open as aioopen
from aiogram import Dispatcher
from aiogram.types import (CallbackQuery, Message, MediaGroup,
                           InputFile, InputMediaVideo, InputMediaPhoto, InputMediaAudio)

from loguru import logger

from tgbot.config import Config
from tgbot.api.instagram import Instagram, CODES
from tgbot.api.youtube import (
    youtube_video_download, youtube_audio_download,
    get_main_data, save_thumbnail, get_thumbnail)
from tgbot.models.user import User
from tgbot.models.link import Link
from tgbot.models.file import File
from tgbot.keyboards.inline import UserInline
from tgbot.misc.utils import (
    SPP_SM_BASE_URLS, is_url,
    is_allowed_social_media, clean_url,
    show_format_sizes
)


class Sender(object):
    async def gen_caption(self, bot) -> str:
        bot = await bot.get_me()
        return f"Downloaded via @{bot.username}"

    async def get_album_file_ids(self, album_message: list) -> str:
        file_ids = []
        for msg in album_message:
            if msg.photo:
                file_ids.append(f"{msg.photo[0].file_id}|image")
            elif msg.video:
                file_ids.append(f"{msg.video.file_id}||video")
        return ",".join(file_ids)

    async def send_image_from_path(self, obj: Message, path: str, chat_id: int) -> str:
        caption = await self.gen_caption(obj.bot)
        async with aioopen(path, 'rb') as f:
            msg = await obj.bot.send_photo(chat_id, f, caption=caption)
            # Return file's telegram id
            return msg.photo[0].file_id

    async def send_video_from_path(self, obj: Message, path: str, chat_id: int) -> str:
        caption = await self.gen_caption(obj.bot)
        async with aioopen(path, 'rb') as f:
            msg = await obj.bot.send_video(chat_id, f, caption=caption)
            return msg.video.file_id

    async def send_album_from_path(self, obj: Message, path: str, chat_id: int) -> str:
        caption = await self.gen_caption(obj.bot)
        media = MediaGroup()
        # Get all files in path (directory)
        for index, f in enumerate(os.listdir(path)):
            file_path = os.path.join(path, f)
            if os.path.isfile(file_path):
                file_type = f.split(".")[-1]
                logger.debug(f"File: {file_path}")
                async with aioopen(file_path, 'rb') as f:
                    if file_type in ["jpg", "jpeg", "png", "gif", "webp"]:
                        if index == 0:
                            media.attach_photo(
                                InputFile(f), caption)
                        else:
                            media.attach_photo(
                                InputFile(f))
                    elif file_type in ["mp4", "mov", "avi", "mkv"]:
                        if index == 0:
                            media.attach_video(
                                InputFile(f), caption)
                        else:
                            media.attach_video(
                                InputFile(f))
        # Send as album
        msg = await obj.bot.send_media_group(chat_id, media)
        return await self.get_album_file_ids(msg)

    async def send_image_from_id(self, obj: Message, file_id: str, chat_id: int) -> str:
        caption = await self.gen_caption(obj.bot)
        msg = await obj.bot.send_photo(chat_id, file_id, caption=caption)
        return msg.photo[0].file_id

    async def send_video_from_id(self, obj: Message, file_id: str, chat_id: int) -> str:
        caption = await self.gen_caption(obj.bot)
        msg = await obj.bot.send_video(chat_id, file_id, caption=caption)
        return msg.video.file_id

    async def send_album_from_ids(self, obj: Message, file_ids: str, chat_id: int) -> str:
        caption = await self.gen_caption(obj.bot)
        media = MediaGroup()
        file_ids = file_ids.split(",")
        for index, file_id in enumerate(file_ids):
            file = file_id.split("|")
            if file[1] == "image":
                if index == 0:
                    media.attach_photo(file[0], caption)
                else:
                    media.attach_photo(file[0])
            elif file[1] == "video":
                if index == 0:
                    media.attach_video(file[0], caption)
                else:
                    media.attach_video(file[0])
        await obj.bot.send_media_group(chat_id, media)


async def user_start(m: Message):
    logger.info(f"User {m.from_user.id} pressed /start")
    await m.reply(
        "Hello! This is a MVP version of this bot.\n"
        "Send me a link to the image or video and I will download it for you!\n"
        "Supported social media:\n"
        "    ○ Instagram\n"
        "    ○ Youtube\n")


async def user_downloader(m: Message, db_user: User):
    config: Config = m.bot.get('config')
    db = m.bot.get('db')
    url = m.text
    logger.info(f"User {m.from_user.id} is trying to download {url}")

    if not await is_url(url):
        await m.reply("Invalid url!")
        return

    social_media = await is_allowed_social_media(url)
    if not social_media:
        await m.reply("This url is not in supported social media!")
        return

    text = "Preparing..."
    is_already_downloaded = await Link.get_link(db, await clean_url(url))
    if is_already_downloaded:
        logger.info(
            f"User {m.from_user.id} is trying to download an already downloaded link")
        await m.reply(text)
        link = is_already_downloaded
        file = await link.get_file(db)
        try:
            await m.reply("Sending...")
            url = await clean_url(url)
            if file.type == 'image':
                await Sender().send_image_from_id(m, file.telegram_file_id, m.chat.id)
            elif file.type == 'video':
                await Sender().send_video_from_id(m, file.telegram_file_id, m.chat.id)
            elif file.type == 'carousel':
                await Sender().send_album_from_ids(m, file.telegram_file_id, m.chat.id)
            else:
                raise
            return
        except Exception as e:
            logger.warning(
                f"User {m.from_user.id} could not upload {file}.")
            await m.reply("Something went wrong. Please try again later.")
            raise e

    text += "\nYou're first who asked for this :)"
    await m.reply(text)

    if SPP_SM_BASE_URLS.INSTAGRAM.value == social_media:
        logger.info(f"User {m.from_user.id} url from Instagram")
        insta = Instagram(config.instagram.username, config.instagram.password)
        result = await insta.download_post(url)
        if type(result) in [int, None]:
            if result in [CODES.COULD_NOT_LOGIN.value,
                          CODES.COULD_NOT_DOWNLOAD,
                          CODES.ERROR.value]:
                logger.error(f"User {m.from_user.id} could not download {url}.\n"
                             f"Error code: {result}")
                await m.reply("Could not download. Please try again later.")
                return

            if result == CODES.NOT_FOUND.value:
                logger.warning(f"User {m.from_user.id} could not download {url}.\n"
                               f"Not found: {result}")
                await m.reply("Could not find post. Maybe it was deleted, "
                              "you typed the wrong url or this is private profile.")
                return

        if type(result) == tuple:
            logger.success(f"User {m.from_user.id} downloaded {url}")
            if result[0] == CODES.DOWNLOADED.value:
                try:
                    result = result[1]
                    await m.reply("Downloaded! Sending...")
                    url = await clean_url(url)
                    if result['file_type'] == 'image':
                        r = await Sender().send_image_from_path(m, result['path'], m.chat.id)
                        file = File("image", result['path'], r)
                        file = await File.add_file(db, file)
                        link = Link(
                            url, SPP_SM_BASE_URLS.INSTAGRAM.name, file.id, db_user.id)
                        await Link.add_link(db, link)
                    elif result['file_type'] == 'video':
                        r = await Sender().send_video_from_path(m, result['path'], m.chat.id)
                        file = File("video", result['path'], r)
                        file = await File.add_file(db, file)
                        link = Link(
                            url, SPP_SM_BASE_URLS.INSTAGRAM.name, file.id, db_user.id)
                        await Link.add_link(db, link)
                    elif result['file_type'] == 'carousel':
                        r = await Sender().send_album_from_path(m, result['path'], m.chat.id)
                        file = File("carousel", result['path'], r)
                        file = await File.add_file(db, file)
                        link = Link(
                            url, SPP_SM_BASE_URLS.INSTAGRAM.name, file.id, db_user.id)
                        await Link.add_link(db, link)
                    else:
                        raise
                    logger.success(
                        f"User {m.from_user.id} successfully sended {url}")
                    return
                except Exception as e:
                    logger.warning(
                        f"User {m.from_user.id} could not upload {result['path']}.")
                    await m.reply("Something went wrong. Please try again later.")
                    raise e

    elif social_media in (SPP_SM_BASE_URLS.YOUTUBE.value,
                          SPP_SM_BASE_URLS.YOUTUBE_SHORT.value):
        main_data = await get_main_data(url)
        thumb = InputFile(await save_thumbnail(main_data['id'], main_data['thumbnail']))
        sizes = await show_format_sizes(main_data['video_formats'])
        text = \
            f"📹 <b>{main_data['title']}</b> <a href=\"{url}\">→</a>\n"\
            f"📺 #{main_data['channel'].replace(' ', '_')} "\
            f"<a href=\"{main_data['channel_url']}\">→</a>\n\n"\
            f"{sizes}"\
            "\n\n<b>Choose type and quality ↓</b>\n"
        markup = await UserInline.generate_download_options(
            video_id=main_data['id'],
            duration=main_data['duration'],
            video_formats=main_data['video_formats'],
            audio_formats=main_data['audio_formats']
        )
        await m.answer_photo(thumb, text, reply_markup=markup)


async def yt_callback_download(cb: CallbackQuery, callback_data: dict):
    logger.info(f"User {cb.from_user.id} selected download option")
    await cb.answer()
    # old_text = cb.message.text if cb.message.text else ""
    # await cb.message.edit_text(old_text + "\n\n⬇️ Downloading...")
    await cb.message.edit_reply_markup(reply_markup='')
    type = callback_data['type']
    video_id = callback_data['video_id']
    format_id = callback_data['format_id']
    width = callback_data['width']
    height = callback_data['height']
    duration = callback_data['duration']
    url = f"https://youtu.be/{video_id}"
    thumb = await get_thumbnail(video_id)
    logger.debug(f"User {cb.from_user.id} selected {callback_data}")

    if type == 'video':
        logger.info(f"User {cb.from_user.id} selected video download")
        result = await youtube_video_download(video_id, format_id, height, url)
        logger.success(
            f"User {cb.from_user.id} downloaded {url}, now sending...")
        await cb.message.answer_video(
            InputFile(result),
            duration=duration,
            thumb=thumb,
            caption="@MediaSavingBot",
            width=width,
            height=height,
            supports_streaming=True
        )

    elif type == 'audio':
        logger.info(f"User {cb.from_user.id} selected audio download")
        result = await youtube_audio_download(video_id, format_id, url)
        logger.success(
            f"User {cb.from_user.id} downloaded {url}, now sending...")
        await cb.message.answer_audio(
            InputFile(result),
            duration=duration,
            thumb=thumb,
            caption="@MediaSavingBot",
            performer="@MediaSavingBot",
            title="@MediaSavingBot"
        )


def register_user(dp: Dispatcher):
    dp.register_message_handler(
        user_start,
        commands=["start"],
        state="*"
    )
    dp.register_message_handler(
        user_downloader,
        content_types=["text"],
        state="*"
    )
    dp.register_callback_query_handler(
        yt_callback_download,
        UserInline.cd_down_options.filter(),
        state="*"
    )
