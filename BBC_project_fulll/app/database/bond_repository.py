import logging
from datetime import datetime

from sqlalchemy import func, select

from app.database.db import async_session_maker
from app.models.bond import Bond as BondModel
from app.schemas.bond import BondData

logger = logging.getLogger(__name__)


class BondRepository:
    """Репозиторий для работы с облигациями."""

    async def save_bonds(self, bonds: list[BondData]) -> None:
        """Сохранить или обновить облигации в БД.

        Args:
            bonds: Список облигаций для сохранения

        Returns:
            None

        Raises:
            Exception: При ошибке сохранения данных
        """
        if not bonds:
            return

        async with async_session_maker() as session:
            try:
                for bond_data in bonds:
                    stmt = select(BondModel).where(BondModel.secid == bond_data.secid)
                    result = await session.execute(stmt)
                    bond = result.scalar_one_or_none()

                    if bond:
                        bond.secname = bond_data.secname
                        bond.listlevel = bond_data.listlevel
                        bond.prevprice = bond_data.prevprice
                        bond.effectiveyield = bond_data.effectiveyield
                        bond.matdate = bond_data.matdate
                        bond.status = bond_data.status
                        bond.couponpercent = bond_data.couponpercent
                        bond.creditrating = bond_data.creditrating
                        bond.facevalue = bond_data.facevalue
                        bond.sectype = bond_data.sectype
                        bond.issuesize = bond_data.issuesize
                        bond.couponfrequency = bond_data.couponfrequency
                        bond.duration = bond_data.duration
                        bond.faceunit = bond_data.faceunit
                        bond.volume = bond_data.volume
                        bond.updated_at = datetime.utcnow()
                    else:
                        bond = BondModel(
                            secid=bond_data.secid,
                            secname=bond_data.secname,
                            listlevel=bond_data.listlevel,
                            prevprice=bond_data.prevprice,
                            effectiveyield=bond_data.effectiveyield,
                            matdate=bond_data.matdate,
                            status=bond_data.status,
                            couponpercent=bond_data.couponpercent,
                            creditrating=bond_data.creditrating,
                            facevalue=bond_data.facevalue,
                            sectype=bond_data.sectype,
                            issuesize=bond_data.issuesize,
                            couponfrequency=bond_data.couponfrequency,
                            duration=bond_data.duration,
                            faceunit=bond_data.faceunit,
                            volume=bond_data.volume,
                        )
                        session.add(bond)

                await session.commit()
                logger.info(f"Сохранено {len(bonds)} облигаций в БД")
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при сохранении облигаций: {e}")
                raise

    async def get_all_bonds(self) -> list[BondData]:
        """Получить все облигации из БД.

        Returns:
            Список всех облигаций из базы данных
        """
        async with async_session_maker() as session:
            stmt = select(BondModel)
            result = await session.execute(stmt)
            bonds_models = result.scalars().all()

            bonds = []
            for bond_model in bonds_models:
                try:
                    bond = BondData(
                        secid=bond_model.secid,
                        secname=bond_model.secname,
                        listlevel=bond_model.listlevel,
                        prevprice=bond_model.prevprice,
                        effectiveyield=bond_model.effectiveyield,
                        matdate=bond_model.matdate,
                        status=bond_model.status,
                        couponpercent=bond_model.couponpercent,
                        creditrating=bond_model.creditrating,
                        facevalue=bond_model.facevalue,
                        sectype=bond_model.sectype,
                        issuesize=bond_model.issuesize,
                        couponfrequency=bond_model.couponfrequency,
                        duration=bond_model.duration,
                        faceunit=bond_model.faceunit,
                        volume=bond_model.volume,
                    )
                    bonds.append(bond)
                except Exception as e:
                    logger.warning(f"Ошибка при создании BondData из модели БД: {e}")
                    continue

            logger.debug(f"Загружено {len(bonds)} облигаций из БД")
            return bonds

    async def get_last_update_time(self) -> datetime | None:
        """Получить время последнего обновления.

        Returns:
            Время последнего обновления или None, если данных нет
        """
        async with async_session_maker() as session:
            stmt = select(func.max(BondModel.updated_at))
            result = await session.execute(stmt)
            last_update = result.scalar()
            return last_update

    async def get_bonds_count(self) -> int:
        """Получить количество облигаций в БД.

        Returns:
            Количество облигаций в базе данных
        """
        async with async_session_maker() as session:
            stmt = select(func.count(BondModel.secid))
            result = await session.execute(stmt)
            count = result.scalar()
            return count or 0
