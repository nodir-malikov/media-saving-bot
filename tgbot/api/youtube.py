import os
import asyncio
import aiohttp
import jmespath
import youtube_dl

from aiofiles import open as aioopen

from loguru import logger

from tgbot.misc.utils import clean_url


ytregex = r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$"
jmesformula = "{id: id, title: title, duration: duration, "\
    "thumbnail: thumbnail, channel_url: channel_url, channel: channel, "\
    "video_formats: (formats[?height && acodec == 'none' && ext == 'mp4' && contains(vcodec, 'avc1.')]."\
    "{width: width, height: height, format_id: format_id, filesize: filesize, fps: fps, "\
    "quality: quality, url: url, vcodec: vcodec, acodec: acodec, ext: ext, "\
    "http_chunk_size: downloader_options.http_chunk_size}), audio_formats: "\
    "(formats[?vcodec == 'none' && acodec != 'none'].{height: height, "\
    "format_id: format_id, filesize: filesize, url: url, acodec: acodec, "\
    "ext: ext, http_chunk_size: downloader_options.http_chunk_size})}"
ytsavepath = os.path.join(os.getcwd(), "media", "youtube")
ytthumbspath = os.path.join(ytsavepath, "thumbs")
ytvideospath = os.path.join(ytsavepath, "videos")
ytauidospath = os.path.join(ytsavepath, "audios")
os.makedirs(ytthumbspath, exist_ok=True)
os.makedirs(ytvideospath, exist_ok=True)
os.makedirs(ytauidospath, exist_ok=True)


async def get_main_data(video_url: str) -> dict:
    """
    Get main data from youtube url
    """
    ydl = youtube_dl.YoutubeDL()
    with ydl:
        r = ydl.extract_info(video_url, download=False)
        data = jmespath.search(jmesformula, r)
        return data


async def save_thumbnail(filename: str, thumb_url: str) -> str:
    """
    Save thumbnail from youtube url
    """
    # TODO : SAVE THUMBNAIL IN ITS OWN EXTENSION BUT THEN CONVERT IT TO JPG VIA pillow
    # extension = str(await clean_url(thumb_url)).split(".")[-1]
    # filepath = os.path.join(ytthumbspath, f"{filename}.{extension}")
    filepath = os.path.join(ytthumbspath, f"{filename}.jpg")
    async with aiohttp.ClientSession() as session:
        async with session.get(thumb_url) as img:
            if img.status == 200:
                async with aioopen(filepath, "wb") as f:
                    await f.write(await img.read())
    return filepath


async def get_thumbnail(video_id: str):
    """
    Get thumbnail from path
    """
    filepath = os.path.join(ytthumbspath, f"{video_id}.jpg")
    return filepath


async def youtube_video_download(id: str, format_id: str, height: str, url: str):
    filepath = os.path.join(ytvideospath, f"{id}_{format_id}_{height}.mp4")
    video_command = [
        "youtube-dl",
        "-c",
        "--embed-subs",
        "-f", f"{format_id}+bestaudio",
        "-o", filepath,
        "--hls-prefer-ffmpeg", url]
    process = await asyncio.create_subprocess_exec(
        *video_command,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    logger.debug(f"YTDL Response: {e_response}")
    filename = t_response.split("Merging formats into")[-1].split('"')[1]
    logger.debug(f"Downloaded video: {filename}")
    return filename


async def youtube_audio_download(id: str, format_id: str, url: str):
    filepath = os.path.join(ytauidospath, f"{id}_{format_id}.mp3")
    audio_command = [
        "youtube-dl",
        "-c",
        "--prefer-ffmpeg",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", format_id,
        "-o", filepath, url]
    process = await asyncio.create_subprocess_exec(
        *audio_command,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    logger.debug(f"YTDL Response: {e_response}")
    filename = t_response.split("Merging formats into")[-1].split('"')[1]
    logger.debug(f"Downloaded audio: {filename}")
    return filename
