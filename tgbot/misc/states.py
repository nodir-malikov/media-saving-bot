from aiogram.dispatcher.filters.state import State, StatesGroup


class UserRegister(StatesGroup):
    wait_lang = State()
