import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.bond import Base

logger = logging.getLogger(__name__)

DATABASE_URL = settings.get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Инициализировать базу данных и создать таблицы.

    Returns:
        None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        try:
            from sqlalchemy import text

            await conn.execute(text("ALTER TABLE bonds ADD COLUMN volume REAL"))
            logger.info("Добавлена колонка volume в таблицу bonds")
        except Exception as e:
            logger.debug(f"Колонка volume уже существует или ошибка миграции: {e}")

    logger.info("База данных инициализирована")
