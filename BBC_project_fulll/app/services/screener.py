import logging
import re
from datetime import datetime

from app.core.config import settings
from app.schemas.bond import BondData, BondScreenResult, FilteredBond

logger = logging.getLogger(__name__)


class BondScreener:
    """Логика фильтрации."""

    RATING_HIERARCHY = [
        "AAA",
        "AA+",
        "AA",
        "AA-",
        "A+",
        "A",
        "A-",
        "BBB+",
        "BBB",
        "BBB-",
        "BB+",
        "BB",
        "BB-",
        "B+",
        "B",
        "B-",
        "CCC+",
        "CCC",
        "CCC-",
        "CC",
        "C",
        "D",
    ]

    def _normalize_rating(self, rating: str | None) -> str | None:
        """Нормализовать рейтинг к стандартному формату.

        Args:
            rating: Рейтинг для нормализации

        Returns:
            Нормализованный рейтинг или None
        """
        if not rating:
            return None

        rating = rating.strip().upper()
        rating = re.sub(r"[^A-Z0-9+\-]", "", rating)

        return rating if rating else None

    def _get_rating_priority(self, rating: str | None) -> int:
        """Получить приоритет рейтинга (меньше = выше рейтинг).

        Args:
            rating: Рейтинг для определения приоритета

        Returns:
            Приоритет рейтинга (индекс в иерархии)
        """
        if not rating:
            return len(self.RATING_HIERARCHY)

        normalized = self._normalize_rating(rating)
        if not normalized:
            return len(self.RATING_HIERARCHY)

        try:
            return self.RATING_HIERARCHY.index(normalized)
        except Exception:
            for i, standard_rating in enumerate(self.RATING_HIERARCHY):
                if standard_rating in normalized or normalized in standard_rating:
                    return i
            return len(self.RATING_HIERARCHY)

    def screen_bonds(self, bonds: list[BondData], count: int | None = None) -> BondScreenResult:
        """Поиск недооцененных облигаций в госсекторе.

        Args:
            bonds: Список облигаций для фильтрации
            count: Количество облигаций для возврата

        Returns:
            Результат скрининга с отфильтрованными облигациями
        """
        filtered = []
        ofz_bonds = []

        for bond in bonds:
            if bond.listlevel != 1:
                continue
            if bond.status != "A":
                continue
            if not bond.prevprice or not bond.effectiveyield:
                continue

            if bond.matdate:
                try:
                    mat_date = datetime.strptime(bond.matdate, "%Y-%m-%d")
                    if mat_date < datetime.now():
                        continue
                except (ValueError, TypeError) as e:
                    logger.debug(f"Ошибка парсинга даты погашения для {bond.secid}: {e}")
                    continue

            bond_name_upper = bond.secname.upper()
            bond_ticker_upper = bond.secid.upper()
            is_ofz = "ОФЗ" in bond_name_upper or "SU" in bond_ticker_upper[:2]

            if is_ofz:
                ofz_bonds.append(bond)

        if not ofz_bonds:
            return BondScreenResult(
                bonds=[],
                total_fetched=len(bonds),
                total_filtered=0,
                boards=settings.get_boards_list(),
            )

        ofz_with_yield = [b for b in ofz_bonds if b.effectiveyield]
        avg_yield = sum(b.effectiveyield for b in ofz_with_yield) / len(ofz_with_yield) if ofz_with_yield else 0
        min_yield_avg = avg_yield + 0.2 if avg_yield > 0 else 0
        min_yield_key_rate = settings.key_rate + 0.3
        min_yield = min(min_yield_key_rate, min_yield_avg) if min_yield_avg > 0 else min_yield_key_rate

        logger.info(
            f"Найдено ОФЗ: {len(ofz_bonds)}, со средней доходностью: {avg_yield:.2f}%, мин. доходность: {min_yield:.2f}%"
        )

        for bond in ofz_bonds:
            if bond.prevprice and bond.prevprice >= 98.5:
                logger.debug(f"{bond.secid}: цена {bond.prevprice}% >= 98.5%")
                continue

            if bond.effectiveyield and bond.effectiveyield <= min_yield:
                logger.debug(f"{bond.secid}: доходность {bond.effectiveyield}% <= {min_yield}%")
                continue

            if bond.effectiveyield and avg_yield > 0 and bond.effectiveyield <= avg_yield:
                logger.debug(f"{bond.secid}: доходность {bond.effectiveyield}% <= среднерыночной {avg_yield:.2f}%")
                continue

            duration_years = None
            if bond.duration:
                duration_years = bond.duration / 365.25
            elif bond.matdate:
                try:
                    mat_date = datetime.strptime(bond.matdate, "%Y-%m-%d")
                    days_to_maturity = (mat_date - datetime.now()).days
                    duration_years = days_to_maturity / 365.25
                except (ValueError, TypeError):
                    pass

            if duration_years and duration_years >= 2.5:
                logger.debug(f"{bond.secid}: дюрация {duration_years:.2f} лет (или {bond.duration} дней) >= 2.5 лет")
                continue

            filtered.append(bond)
            logger.debug(f"{bond.secid}: прошла все фильтры")

        logger.info(f"После фильтрации осталось: {len(filtered)} облигаций")

        if not filtered:
            return BondScreenResult(
                bonds=[],
                total_fetched=len(bonds),
                total_filtered=0,
                boards=settings.get_boards_list(),
            )

        filtered.sort(key=lambda x: x.effectiveyield or 0, reverse=True)

        bonds_count = count if count is not None else settings.top_bonds_count
        top_bonds = filtered[:bonds_count]

        result_bonds = []
        DEFAULT_NOMINAL = 1000.0
        for b in top_bonds:
            nominal = b.facevalue if b.facevalue else DEFAULT_NOMINAL
            price_rub = (b.prevprice * nominal / 100) if b.prevprice else 0.0
            course = b.prevprice if b.prevprice else 0.0
            currency = b.faceunit if b.faceunit else "RUB"
            result_bonds.append(
                FilteredBond(
                    ticker=b.secid,
                    name=b.secname,
                    price=price_rub,
                    course_percent=course,
                    maturity_date=b.matdate or "Н/Д",
                    coupon_rate=b.couponpercent,
                    currency=currency,
                )
            )

        return BondScreenResult(
            bonds=result_bonds,
            total_fetched=len(bonds),
            total_filtered=len(filtered),
            boards=settings.get_boards_list(),
        )

    def screen_conservative(self, bonds: list[BondData], count: int | None = None) -> BondScreenResult:
        """Консервативная стратегия: ОФЗ и квазигосударственные, рейтинг BBB+, дюрация до 4 лет.

        Args:
            bonds: Список облигаций для фильтрации
            count: Количество облигаций для возврата

        Returns:
            Результат скрининга с отфильтрованными облигациями
        """
        filtered = []

        quasi_govt_keywords = [
            "РЖД",
            "ГАЗПРОМ",
            "РОСНЕФТЬ",
            "ЛУКОЙЛ",
            "СБЕРБАНК",
            "ВТБ",
            "ВЭБ",
            "АИЖК",
            "ДОМ.РФ",
            "РОССЕТИ",
            "ТРАНСНЕФТЬ",
            "АТОМЭНЕРГОПРОМ",
            "ОФЗ",
            "МИНФИН",
        ]

        for bond in bonds:
            if bond.listlevel != 1:
                continue
            if bond.status != "A":
                continue
            if not bond.prevprice or not bond.effectiveyield:
                continue

            if bond.matdate:
                try:
                    mat_date = datetime.strptime(bond.matdate, "%Y-%m-%d")
                    if mat_date < datetime.now():
                        continue
                except (ValueError, TypeError) as e:
                    logger.debug(f"Ошибка парсинга даты погашения для {bond.secid}: {e}")
                    continue

            bond_name_upper = bond.secname.upper()
            bond_ticker_upper = bond.secid.upper()

            is_ofz = "ОФЗ" in bond_name_upper or "SU" in bond_ticker_upper[:2]
            is_quasi_govt = any(keyword in bond_name_upper for keyword in quasi_govt_keywords)

            if not (is_ofz or is_quasi_govt):
                continue

            if bond.creditrating:
                rating_priority = self._get_rating_priority(bond.creditrating)
                bbb_priority = self._get_rating_priority("BBB-")
            if rating_priority > bbb_priority:
                continue

            duration_years = None
            if bond.duration:
                duration_years = bond.duration / 365.25
            elif bond.matdate:
                try:
                    mat_date = datetime.strptime(bond.matdate, "%Y-%m-%d")
                    days_to_maturity = (mat_date - datetime.now()).days
                    duration_years = days_to_maturity / 365.25
                except (ValueError, TypeError) as e:
                    logger.debug(f"Ошибка расчета дюрации для {bond.secid}: {e}")

            if duration_years and duration_years > 4.0:
                continue

            filtered.append(bond)

        if not filtered:
            return BondScreenResult(
                bonds=[],
                total_fetched=len(bonds),
                total_filtered=0,
                boards=settings.get_boards_list(),
            )

        filtered.sort(key=lambda x: x.effectiveyield or 0, reverse=True)

        bonds_count = count if count is not None else settings.top_bonds_count
        top_bonds = filtered[:bonds_count]

        result_bonds = []
        DEFAULT_NOMINAL = 1000.0
        for b in top_bonds:
            nominal = b.facevalue if b.facevalue else DEFAULT_NOMINAL
            price_rub = (b.prevprice * nominal / 100) if b.prevprice else 0.0
            course = b.prevprice if b.prevprice else 0.0
            currency = b.faceunit if b.faceunit else "RUB"
            result_bonds.append(
                FilteredBond(
                    ticker=b.secid,
                    name=b.secname,
                    price=price_rub,
                    course_percent=course,
                    maturity_date=b.matdate or "Н/Д",
                    coupon_rate=b.couponpercent,
                    currency=currency,
                )
            )

        return BondScreenResult(
            bonds=result_bonds,
            total_fetched=len(bonds),
            total_filtered=len(filtered),
            boards=settings.get_boards_list(),
        )

    def screen_high_yield(self, bonds: list[BondData], count: int | None = None) -> BondScreenResult:
        """Высокодоходная стратегия: доходность > 13%, рейтинг A/BBB, купон ежеквартальный.

        Args:
            bonds: Список облигаций для фильтрации
            count: Количество облигаций для возврата

        Returns:
            Результат скрининга с отфильтрованными облигациями
        """
        filtered = []

        for bond in bonds:
            if bond.listlevel != 1:
                continue
            if bond.status != "A":
                continue
            if not bond.prevprice or not bond.effectiveyield:
                continue

            if bond.matdate:
                try:
                    mat_date = datetime.strptime(bond.matdate, "%Y-%m-%d")
                    if mat_date < datetime.now():
                        continue
                except (ValueError, TypeError) as e:
                    logger.debug(f"Ошибка парсинга даты погашения для {bond.secid}: {e}")
                    continue

            if bond.effectiveyield <= 13.0:
                continue

            if bond.creditrating:
                rating_priority = self._get_rating_priority(bond.creditrating)
                a_plus_priority = self._get_rating_priority("A+")
                bbb_minus_priority = self._get_rating_priority("BBB-")

                if rating_priority < a_plus_priority or rating_priority > bbb_minus_priority:
                    continue

            if bond.couponfrequency is not None and bond.couponfrequency != 4:
                continue

            filtered.append(bond)

        if not filtered:
            return BondScreenResult(
                bonds=[],
                total_fetched=len(bonds),
                total_filtered=0,
                boards=settings.get_boards_list(),
            )

        filtered.sort(key=lambda x: x.effectiveyield or 0, reverse=True)

        bonds_count = count if count is not None else settings.top_bonds_count
        top_bonds = filtered[:bonds_count]

        result_bonds = []
        DEFAULT_NOMINAL = 1000.0
        for b in top_bonds:
            nominal = b.facevalue if b.facevalue else DEFAULT_NOMINAL
            price_rub = (b.prevprice * nominal / 100) if b.prevprice else 0.0
            course = b.prevprice if b.prevprice else 0.0
            currency = b.faceunit if b.faceunit else "RUB"
            result_bonds.append(
                FilteredBond(
                    ticker=b.secid,
                    name=b.secname,
                    price=price_rub,
                    course_percent=course,
                    maturity_date=b.matdate or "Н/Д",
                    coupon_rate=b.couponpercent,
                    currency=currency,
                )
            )

        return BondScreenResult(
            bonds=result_bonds,
            total_fetched=len(bonds),
            total_filtered=len(filtered),
            boards=settings.get_boards_list(),
        )
