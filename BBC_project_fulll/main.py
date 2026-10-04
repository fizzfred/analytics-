import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.bonds import router as bonds_router
from app.bot.handlers.start import router as start_router
from app.core.config import settings
from app.database.db import init_db
from app.services.data_updater import DataUpdater

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Запуск бота...")

    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        raise ValueError("TELEGRAM_BOT_TOKEN обязателен для работы бота")

    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await init_db()

    # Запуск обновлятора данных
    updater = DataUpdater(update_interval_minutes=5)
    await updater.start()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(bonds_router)

    try:
        await dp.start_polling(bot)
    finally:
        # Остановка обновлятора при завершении работы
        await updater.stop()


if __name__ == "__main__":
    asyncio.run(main())
