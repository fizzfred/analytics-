import asyncio
import logging

import aiohttp

from app.core.config import settings
from app.schemas.bond import BondData

logger = logging.getLogger(__name__)


class MOEXClient:
    """Клиент для MOEX API."""

    def __init__(self):
        self.base_url = settings.moex_base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _request(self, url: str, params: dict | None = None) -> dict:
        """Выполнить запрос.

        Args:
            url: URL для запроса
            params: Параметры запроса

        Returns:
            Словарь с данными ответа или пустой словарь при ошибке
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Неожиданный статус ответа {resp.status} для {url}")
                    return {}
        except Exception as e:
            logger.error(f"Ошибка запроса {url}: {e}")
            return {}

    def _parse_response(self, data: dict) -> list[BondData]:
        """Парсинг ответа.

        Args:
            data: Данные ответа от MOEX API

        Returns:
            Список облигаций
        """
        bonds = []
        try:
            securities = data.get("securities", {})
            marketdata = data.get("marketdata", {})

            sec_cols = securities.get("columns", [])
            sec_data = securities.get("data", [])

            mkt_cols = marketdata.get("columns", [])
            mkt_data = marketdata.get("data", [])

            market_map = {}
            if "SECID" in mkt_cols:
                secid_idx = mkt_cols.index("SECID")
                for row in mkt_data:
                    market_map[row[secid_idx]] = dict(zip(mkt_cols, row, strict=False))

            for row in sec_data:
                bond_dict = dict(zip(sec_cols, row, strict=False))
                secid = bond_dict.get("SECID")

                if secid in market_map:
                    bond_dict.update(market_map[secid])

                data_lower = {k.lower(): v for k, v in bond_dict.items()}

                try:
                    if data_lower.get("listlevel"):
                        data_lower["listlevel"] = int(data_lower["listlevel"])
                    if data_lower.get("prevprice"):
                        data_lower["prevprice"] = float(data_lower["prevprice"])
                    if data_lower.get("yieldatprevwaprice"):
                        data_lower["yieldatprevwaprice"] = float(data_lower["yieldatprevwaprice"])
                    if data_lower.get("couponpercent"):
                        data_lower["couponpercent"] = float(data_lower["couponpercent"])
                    if data_lower.get("facevalue"):
                        data_lower["facevalue"] = float(data_lower["facevalue"])
                    if data_lower.get("issuesize"):
                        data_lower["issuesize"] = float(data_lower["issuesize"])
                    if data_lower.get("couponfrequency"):
                        data_lower["couponfrequency"] = int(data_lower["couponfrequency"])
                    if data_lower.get("duration"):
                        data_lower["duration"] = float(data_lower["duration"])
                    if data_lower.get("volume"):
                        data_lower["volume"] = float(data_lower["volume"])

                    bonds.append(BondData(**data_lower))
                except Exception as e:
                    logger.debug(f"Ошибка при создании BondData для {secid}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

        return bonds

    async def _fetch_board(self, board: str) -> list[BondData]:
        """Получить облигации для одного режима торгов.

        Args:
            board: Режим торгов (например, TQCB, TQOB)

        Returns:
            Список облигаций для указанного режима торгов
        """
        url = f"{self.base_url}/iss/engines/stock/markets/bonds/boards/{board}/securities.json"
        params = {
            "iss.meta": "off",
            "iss.only": "securities,marketdata",
            "securities.columns": "SECID,SECNAME,MATDATE,STATUS,LISTLEVEL,PREVPRICE,YIELDATPREVWAPRICE,COUPONPERCENT,FACEVALUE,SECTYPE,ISSUESIZE,COUPONFREQUENCY,DURATION,CREDITRATING,FACEUNIT",
            "marketdata.columns": "SECID,DURATION,VOLUME",
        }

        data = await self._request(url, params)
        return self._parse_response(data)

    async def fetch_all_boards(self) -> list[BondData]:
        """Получить все облигации с параллельной обработкой запросов.

        Returns:
            Список всех облигаций со всех режимов торгов
        """
        boards = settings.get_boards_list()

        if not boards:
            logger.warning("Список режимов торгов пуст")
            return []

        tasks = [self._fetch_board(board) for board in boards]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_bonds = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при получении данных для режима {boards[i]}: {result}")
            else:
                all_bonds.extend(result)

        return all_bonds
