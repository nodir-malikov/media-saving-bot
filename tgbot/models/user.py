from sqlalchemy import (Column, String, BigInteger, DateTime,
                        insert, update, func, select)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import BigInteger

from tgbot.services.db_base import Base


class User(Base):
    __tablename__ = "user"
    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    firstname = Column(String(length=200))
    lastname = Column(String(length=200))
    username = Column(String(length=200))
    lang_code = Column(String(length=10), default='ru')
    created_at = Column(DateTime, default=func.now())

    def __init__(self, telegram_id: int, firstname: str, lastname: str,
                 username: str, lang_code: str = "ru"):
        self.telegram_id = telegram_id
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.lang_code = lang_code

    @classmethod
    async def get_user(cls, db_session: sessionmaker, telegram_id: int) -> 'User':
        async with db_session() as db_session:
            sql = select([User]).where(User.telegram_id == telegram_id)
            result = await db_session.execute(sql)
            return result.scalar()

    @classmethod
    async def add_user(cls, db_session: sessionmaker, user: 'User') -> 'User':
        async with db_session() as db_session:
            sql = insert(User).values(
                telegram_id=user.telegram_id,
                firstname=user.firstname,
                lastname=user.lastname,
                username=user.username,
                lang_code=user.lang_code
            ).returning('*')
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.scalar()

    async def update_user(self, db_session: sessionmaker, user: 'User') -> 'User':
        async with db_session() as db_session:
            sql = update(User).where(User.telegram_id == self.telegram_id).values(
                firstname=user.firstname,
                lastname=user.lastname,
                username=user.username,
                lang_code=user.lang_code
            )
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.scalar()

    @classmethod
    async def get_all_users(cls, db_session: sessionmaker) -> list:
        async with db_session() as db_session:
            sql = select([User])
            result = await db_session.execute(sql)
            return result.fetchall()

    @classmethod
    async def count_users(cls, db_session: sessionmaker) -> int:
        async with db_session() as db_session:
            sql = select([func.count(User.id)]).select_from(User)
            result = await db_session.execute(sql)
            return result.scalar()[0]

    def __repr__(self):
        return f'User (id: {self.telegram_id}, firstname: {self.firstname}, ' \
            f'lastname: {self.lastname}, username: {self.username}, lang_code: {self.lang_code})'
