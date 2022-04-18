from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData


class UserInline:
    cd_down_options = CallbackData(
        "yt", "type", "video_id", "format_id", "width", "height", "duration"
    )

    @classmethod
    async def generate_download_options(cls, video_id: str,
                                        duration: int,
                                        video_formats: list,
                                        audio_formats: list
                                        ) -> InlineKeyboardMarkup:
        """
        Generate inline keyboard for download options
        """
        video_kb = []
        audio_kb = []
        markup = InlineKeyboardMarkup(row_width=3)

        for index, format in enumerate(video_formats):
            video_kb.append(
                InlineKeyboardButton(
                    text=f"📹 {format['height']}p",
                    callback_data=cls.cd_down_options.new(
                        type="video",
                        video_id=video_id,
                        format_id=format['format_id'],
                        width=format['width'],
                        height=format['height'],
                        duration=duration
                    )
                )
            )

            if index % 3 == 2:
                markup.row(*video_kb)
                video_kb = []

        markup.row(*video_kb)

        audio_kb.append(
            InlineKeyboardButton(
                text=f"🎵 MP3",
                callback_data=cls.cd_down_options.new(
                    type="audio",
                    video_id=video_id,
                    format_id=audio_formats[-1]['format_id'],
                    width=0,
                    height=0,
                    duration=duration
                )
            )
        )

        markup.row(*audio_kb)

        return markup
