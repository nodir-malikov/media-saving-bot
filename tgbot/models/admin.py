from sqlalchemy import (Column, String, BigInteger, DateTime,
                        insert, update, func, delete, select)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import BigInteger

from tgbot.services.db_base import Base


class Admin(Base):
    __tablename__ = "admin"
    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(String(length=50), unique=True)
    created_at = Column(DateTime, default=func.now())

    def __init__(self, telegram_id: str):
        self.telegram_id = telegram_id

    @classmethod
    async def get_admin(cls, db_session: sessionmaker, telegram_id: str) -> 'Admin':
        async with db_session() as db_session:
            sql = select([Admin]).where(Admin.telegram_id == telegram_id)
            result = await db_session.execute(sql)
            return result.scalar()

    @classmethod
    async def add_admin(cls, db_session: sessionmaker, admin: 'Admin') -> 'Admin':
        async with db_session() as db_session:
            sql = insert(Admin).values(
                telegram_id=admin.telegram_id
            ).returning('*')
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.first()

    @classmethod
    async def get_all_admins(cls, db_session: sessionmaker) -> list:
        async with db_session() as db_session:
            sql = select([Admin])
            result = await db_session.execute(sql)
            return result.fetchall()

    @classmethod
    async def count_admins(cls, db_session: sessionmaker) -> int:
        async with db_session() as db_session:
            sql = select([Admin]).count()
            result = await db_session.execute(sql)
            return result.scalar()[0]

    async def update_admin(self, db_session: sessionmaker, admin: 'Admin') -> 'Admin':
        async with db_session() as db_session:
            sql = update(Admin).where(Admin.telegram_id == self.telegram_id).values(
                telegram_id=admin.telegram_id
            )
            result = await db_session.execute(sql)
            await db_session.commit()
            return result.scalar()

    @classmethod
    async def delete_admin(cls, db_session: sessionmaker, telegram_id: str) -> None:
        async with db_session() as db_session:
            sql = delete(Admin).where(Admin.telegram_id == telegram_id)
            await db_session.execute(sql)
            await db_session.commit()

    def __repr__(self):
        return f"<Admin(id='{self.id}', telegram_id='{self.telegram_id}')>"
