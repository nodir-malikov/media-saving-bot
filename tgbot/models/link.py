from sqlalchemy import (Column, String, BigInteger, DateTime, ForeignKey,
                        insert, update, func, delete, select)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import BigInteger

from tgbot.services.db_base import Base
from tgbot.misc.utils import clean_url
from tgbot.models.user import User
from tgbot.models.file import File


class Link(Base):
    __tablename__ = "link"
    id = Column(BigInteger, primary_key=True)
    url = Column(String(length=255), unique=True)
    social_media = Column(String(length=50))
    created_at = Column(DateTime, default=func.now())
    file_id = Column(BigInteger, ForeignKey(File.id, ondelete='SET NULL'))
    user_id = Column(BigInteger, ForeignKey(User.id, ondelete='SET NULL'))

    def __init__(self, url: str, social_media: str, file_id: int, user_id: int):
        self.url = url
        self.social_media = social_media
        self.file_id = file_id
        self.user_id = user_id

    @classmethod
    async def get_link(cls, db_session: sessionmaker, url: str) -> 'Link':
        async with db_session() as db_session:
            sql = select([Link]).where(Link.url == await clean_url(url))
            result = await db_session.execute(sql)
            return result.scalar()

    @classmethod
    async def add_link(cls, db_session: sessionmaker, link: 'Link') -> 'Link':
        async with db_session() as db_session:
            sql = insert(Link).values(
                url=await clean_url(link.url),
                social_media=link.social_media,
                file_id=link.file_id,
                user_id=link.user_id
            ).returning('*')
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.scalar()

    @classmethod
    async def get_all_links(cls, db_session: sessionmaker) -> list:
        async with db_session() as db_session:
            sql = select([Link])
            result = await db_session.execute(sql)
            return await result.fetchall()

    @classmethod
    async def count_links(cls, db_session: sessionmaker) -> int:
        async with db_session() as db_session:
            sql = select([Link]).count()
            result = await db_session.execute(sql)
            return await result.fetchone()[0]

    async def update_link(self, db_session: sessionmaker, link: 'Link') -> 'Link':
        async with db_session() as db_session:
            sql = update(Link).where(Link.url == self.url).values(
                url=await clean_url(link.url),
                social_media=link.social_media,
                file_id=link.file_id,
                user_id=link.user_id
            )
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.scalar()

    async def delete_link(self, db_session: sessionmaker) -> None:
        async with db_session() as db_session:
            sql = delete(Link).where(await clean_url(Link.url) == self.url)
            await db_session.execute(sql)
            await db_session.commit()

    async def get_user(self, db_session: sessionmaker) -> User:
        async with db_session() as db_session:
            sql = select([User]).where(User.id == self.user_id)
            result = await db_session.execute(sql)
            return result.scalar()

    async def get_file(self, db_session: sessionmaker) -> File:
        async with db_session() as db_session:
            sql = select([File]).where(File.id == self.file_id)
            result = await db_session.execute(sql)
            return result.scalar()

    def __repr__(self):
        return f"<Link(url='{self.url}', social_media='{self.social_media}', "\
            f"created_at='{self.created_at}', file_id='{self.file_id}', user_id='{self.user_id}')>"
