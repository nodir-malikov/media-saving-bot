from aiogram import types
from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

from tgbot.models.user import User


class DbMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    async def pre_process(self, obj, data, *args):
        db_session = obj.bot.get('db')
        telegram_user: types.User = obj.from_user
        user = await User.get_user(db_session=db_session, telegram_id=telegram_user.id)
        if not user:
            new_user = User(telegram_user.id, telegram_user.first_name,
                            telegram_user.last_name, telegram_user.username)
            await User.add_user(db_session, new_user)
        data['db_user'] = user
