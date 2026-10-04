import asyncio
import logging

from app.database.bond_repository import BondRepository
from app.services.moex_client import MOEXClient

logger = logging.getLogger(__name__)


class DataUpdater:
    """Сервис для периодического обновления данных облигаций."""

    def __init__(self, update_interval_minutes: int = 5):
        """
        Инициализировать обновлятор данных.

        Args:
            update_interval_minutes: Интервал обновления в минутах (по умолчанию 5)
        """
        self.update_interval = update_interval_minutes * 60
        self.repository = BondRepository()
        self.is_running = False
        self._task: asyncio.Task | None = None

    async def update_bonds_data(self) -> None:
        """Обновить данные облигаций из MOEX API.

        Returns:
            None
        """
        logger.info("Начало обновления данных облигаций...")
        try:
            async with MOEXClient() as client:
                bonds = await client.fetch_all_boards()

            if bonds:
                await self.repository.save_bonds(bonds)
                logger.info(f"Данные обновлены: {len(bonds)} облигаций")
            else:
                logger.warning("Не получено облигаций от MOEX API")

        except Exception as e:
            logger.error(f"Ошибка при обновлении данных облигаций: {e}")

    async def start(self) -> None:
        """Запустить фоновую задачу обновления данных.

        Returns:
            None
        """
        if self.is_running:
            logger.warning("Обновлятор данных уже запущен")
            return

        self.is_running = True
        logger.info(f"Запуск обновлятора данных (интервал: {self.update_interval / 60} минут)")

        await self.update_bonds_data()

        self._task = asyncio.create_task(self._update_loop())

    async def stop(self) -> None:
        """Остановить фоновую задачу обновления данных.

        Returns:
            None
        """
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Обновлятор данных остановлен")

    async def _update_loop(self) -> None:
        """Цикл периодического обновления данных.

        Returns:
            None
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.update_interval)
                if self.is_running:
                    await self.update_bonds_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления данных: {e}")
                await asyncio.sleep(60)
