from sqlalchemy import (Column, String, BigInteger, DateTime,
                        insert, update, func, delete, select)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import BigInteger

from tgbot.services.db_base import Base


class File(Base):
    __tablename__ = "file"
    id = Column(BigInteger, primary_key=True)
    type = Column(String(length=50))
    path = Column(String(length=500))
    telegram_file_id = Column(String(length=2000), unique=True)
    downloaded_at = Column(DateTime, default=func.now())

    def __init__(self, type: str, path: str,
                 telegram_file_id: str):
        self.type = type
        self.path = path
        self.telegram_file_id = telegram_file_id

    @classmethod
    async def get_file(cls, db_session: sessionmaker, telegram_file_id: str) -> 'File':
        async with db_session() as db_session:
            sql = select([File]).where(
                File.telegram_file_id == telegram_file_id)
            result = await db_session.execute(sql)
            return result.scalar()

    @classmethod
    async def add_file(cls, db_session: sessionmaker, file: 'File') -> 'File':
        async with db_session() as db_session:
            sql = insert(File).values(
                type=file.type,
                path=file.path,
                telegram_file_id=file.telegram_file_id,
            ).returning('*')
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.first()

    @classmethod
    async def get_all_files(cls, db_session: sessionmaker) -> list:
        async with db_session() as db_session:
            sql = select([File])
            result = await db_session.execute(sql)
            return result.fetchall()

    @classmethod
    async def count_files(cls, db_session: sessionmaker) -> int:
        async with db_session() as db_session:
            sql = select([File]).count()
            result = await db_session.execute(sql)
            return result.scalar()[0]

    async def update_file(self, db_session: sessionmaker, file: 'File') -> 'File':
        async with db_session() as db_session:
            sql = update(File).where(File.telegram_file_id == self.telegram_file_id).values(
                type=file.type,
                path=file.path,
                telegram_file_id=file.telegram_file_id,
            )
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.scalar()

    async def delete_file(self, db_session: sessionmaker) -> None:
        async with db_session() as db_session:
            sql = delete(File).where(
                File.telegram_file_id == self.telegram_file_id)
            await db_session.execute(sql)
            await db_session.commit()

    async def __repr__(self):
        return f"<File(id={self.id}, type={self.type}, " \
            f"path={self.path}, " \
            f"telegram_file_id={self.telegram_file_id}, " \
            f"downloaded_at={self.downloaded_at})>"
