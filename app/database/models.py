import os

from dotenv import load_dotenv

from sqlalchemy import BigInteger, String, Text, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine


load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


engine = create_async_engine(f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Worker(Base):
    __tablename__ = "workers"
    id = Column(BigInteger, primary_key=True)
    full_name = Column(Text)
    file_id = Column(String(255))
    chat_id = Column(String(31))
    speciality = Column(String(255))
    phone = Column(String(31))


class Pair(Base):
    __tablename__ = "pairs"
    id = Column(BigInteger, primary_key=True)
    subject = Column(Text)
    object = Column(Text)
    survey = Column(Text)
    weekday = Column(String(31))
    date = Column(String(31))
    status = Column(String(15), default="ready")


class Survey(Base):
    __tablename__ = "surveys"
    id = Column(BigInteger, primary_key=True)
    speciality = Column(String(511))
    question1 = Column(Text)
    question1_type = Column(String(7))
    question2 = Column(Text)
    question2_type = Column(String(7))
    question3 = Column(Text)
    question3_type = Column(String(7))
    question4 = Column(Text)
    question4_type = Column(String(7))
    question5 = Column(Text)
    question5_type = Column(String(7))


class Answer(Base):
    __tablename__ = "answers"
    id = Column(BigInteger, primary_key=True)
    subject = Column(Text)
    object = Column(Text)
    survey = Column(Text)
    survey_date = Column(String(31))
    completed_at = Column(String(63))
    question1 = Column(Text)
    answer1 = Column(Text)
    question2 = Column(Text)
    answer2 = Column(Text)
    question3 = Column(Text)
    answer3 = Column(Text)
    question4 = Column(Text)
    answer4 = Column(Text)
    question5 = Column(Text)
    answer5 = Column(Text)


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
