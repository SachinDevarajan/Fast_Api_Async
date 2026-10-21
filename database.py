import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_async_engine(DATABASE_URL, echo = True)

class Base(DeclarativeBase):
    pass

SessionLocal = async_sessionmaker(
    bind= engine,
    class_= AsyncSession,
    expire_on_commit= False
)

async def get_db():
    async with SessionLocal() as db:
        yield db
        