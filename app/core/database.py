import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text

from app.core.config import Config

logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"mysql+aiomysql://{Config.DB_USERNAME}:"
    f"{Config.DB_PASSWORD}@{Config.DB_HOST}:"
    f"{Config.DB_PORT}/{Config.DB_NAME}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# STANDARD ASYNC SESSION MAKER
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


#  Dependency for FastAPI routes
async def get_db():
    async with async_session_maker() as session:
        yield session


# ✅ DB connection check
async def check_database_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error("Database connection failed")
        logger.exception(e)
        raise
