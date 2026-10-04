import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.core.config import settings
from app.database.bond_repository import BondRepository
from app.services.screener import BondScreener

logger = logging.getLogger(__name__)

router = Router()


def _get_currency_symbol(currency: str) -> str:
    """Получить символ валюты.

    Args:
        currency: Код валюты (RUB, USD, EUR и т.д.)

    Returns:
        Символ валюты или код валюты, если символ не найден
    """
    currency_map = {
        "RUB": "₽",
        "SUR": "₽",
        "USD": "$",
        "EUR": "€",
        "CNY": "¥",
        "GBP": "£",
    }
    return currency_map.get(currency, currency)


async def _handle_top_bonds(message: Message, count: int | None = None) -> None:
    """Обработка команды top_bonds.

    Args:
        message: Сообщение от пользователя
        count: Количество облигаций для отображения

    Returns:
        None
    """
    logger.info(f"Получена команда {message.text} от пользователя {message.from_user.id}")
    msg = await message.answer("🔄 Загрузка данных...")

    try:
        repository = BondRepository()
        bonds = await repository.get_all_bonds()

        screener = BondScreener()
        result = screener.screen_bonds(bonds, count=count)

        if not result.bonds:
            await msg.edit_text("❌ Подходящих облигаций не найдено.")
            return

        text = [
            f"🔍 <b>Недооцененные ОФЗ - {len(result.bonds)}</b>",
            f"Всего проверено: {result.total_fetched}",
            f"Прошло фильтр: {result.total_filtered}\n",
            "<i>Критерии: ОФЗ, доходность &gt; ключевая+0.3%, цена &lt;98.5%, дюрация &lt;2.5 лет</i>\n",
        ]

        for i, bond in enumerate(result.bonds, 1):
            coupon = f"{bond.coupon_rate}%" if bond.coupon_rate else "-"
            currency_symbol = _get_currency_symbol(bond.currency)
            text.append(
                f"{i}. <b>{bond.ticker}</b> ({bond.name})\n"
                f"   💰 {bond.price:.2f} {currency_symbol} | 📈 <b>{bond.course_percent:.2f}%</b>\n"
                f"   📅 {bond.maturity_date} | Купон: {coupon}"
            )

        await msg.edit_text("\n".join(text))

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.message(Command("top_bonds"))
async def cmd_top_bonds(message: Message) -> None:
    """Показать топ облигаций.

    Args:
        message: Сообщение от пользователя

    Returns:
        None
    """
    await _handle_top_bonds(message, count=None)


@router.message(F.text.regexp(r"^/top_bonds_\d+"))
async def cmd_top_bonds_with_count(message: Message) -> None:
    """Показать топ облигаций с указанным количеством.

    Args:
        message: Сообщение от пользователя с командой вида /top_bonds_N

    Returns:
        None
    """
    command_text = message.text or ""
    match = re.search(r"/top_bonds_(\d+)", command_text)

    if not match:
        await message.answer("❌ Неверный формат команды. Используйте: /top_bonds_5")
        return

    try:
        count = int(match.group(1))
        if count <= 0:
            await message.answer("❌ Количество должно быть больше нуля.")
            return
        if count > settings.max_bonds_limit:
            await message.answer(f"❌ Максимальное количество: {settings.max_bonds_limit}.")
            return
    except ValueError:
        await message.answer("❌ Неверный формат числа.")
        return

    await _handle_top_bonds(message, count=count)


async def _handle_conservative_bonds(message: Message, count: int | None = None) -> None:
    """Обработка консервативной стратегии.

    Args:
        message: Сообщение от пользователя
        count: Количество облигаций для отображения

    Returns:
        None
    """
    logger.info(f"Консервативная стратегия от пользователя {message.from_user.id}")
    msg = await message.answer("🔄 Загрузка данных для консервативной стратегии...")

    try:
        repository = BondRepository()
        bonds = await repository.get_all_bonds()

        screener = BondScreener()
        result = screener.screen_conservative(bonds, count=count)

        if not result.bonds:
            await msg.edit_text("❌ Подходящих облигаций не найдено по консервативной стратегии.")
            return

        text = [
            f"🛡️ <b>Консервативная стратегия - Топ {len(result.bonds)}</b>",
            f"Всего проверено: {result.total_fetched}",
            f"Прошло фильтр: {result.total_filtered}\n",
            "<i>Критерии: ОФЗ/квазигос., рейтинг &ge;BBB, дюрация &le;4 года</i>\n",
        ]

        for i, bond in enumerate(result.bonds, 1):
            coupon = f"{bond.coupon_rate}%" if bond.coupon_rate else "-"
            currency_symbol = _get_currency_symbol(bond.currency)
            text.append(
                f"{i}. <b>{bond.ticker}</b> ({bond.name})\n"
                f"   💰 {bond.price:.2f} {currency_symbol} | 📈 <b>{bond.course_percent:.2f}%</b>\n"
                f"   📅 {bond.maturity_date} | Купон: {coupon}"
            )

        await msg.edit_text("\n".join(text))

    except Exception as e:
        logger.error(f"Ошибка в консервативной стратегии: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)}")


async def _handle_high_yield_bonds(message: Message, count: int | None = None) -> None:
    """Обработка высокодоходной стратегии.

    Args:
        message: Сообщение от пользователя
        count: Количество облигаций для отображения

    Returns:
        None
    """
    logger.info(f"Высокодоходная стратегия от пользователя {message.from_user.id}")
    msg = await message.answer("🔄 Загрузка данных для высокодоходной стратегии...")

    try:
        repository = BondRepository()
        bonds = await repository.get_all_bonds()

        screener = BondScreener()
        result = screener.screen_high_yield(bonds, count=count)

        if not result.bonds:
            await msg.edit_text("❌ Подходящих облигаций не найдено по высокодоходной стратегии.")
            return

        text = [
            f"🚀 <b>Высокодоходная стратегия - Топ {len(result.bonds)}</b>",
            f"Всего проверено: {result.total_fetched}",
            f"Прошло фильтр: {result.total_filtered}\n",
            "<i>Критерии: доходность &gt;13%, рейтинг A/BBB, купон ежеквартально</i>\n",
        ]

        for i, bond in enumerate(result.bonds, 1):
            coupon = f"{bond.coupon_rate}%" if bond.coupon_rate else "-"
            currency_symbol = _get_currency_symbol(bond.currency)
            text.append(
                f"{i}. <b>{bond.ticker}</b> ({bond.name})\n"
                f"   💰 {bond.price:.2f} {currency_symbol} | 📈 <b>{bond.course_percent:.2f}%</b>\n"
                f"   📅 {bond.maturity_date} | Купон: {coupon}"
            )

        await msg.edit_text("\n".join(text))

    except Exception as e:
        logger.error(f"Ошибка в высокодоходной стратегии: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.message(Command("conservative"))
async def cmd_conservative(message: Message) -> None:
    """Консервативная стратегия.

    Args:
        message: Сообщение от пользователя

    Returns:
        None
    """
    await _handle_conservative_bonds(message, count=None)


@router.message(Command("high_yield"))
async def cmd_high_yield(message: Message) -> None:
    """Высокодоходная стратегия.

    Args:
        message: Сообщение от пользователя

    Returns:
        None
    """
    await _handle_high_yield_bonds(message, count=None)


@router.callback_query(F.data == "strategy_top")
async def callback_strategy_top(callback: CallbackQuery) -> None:
    """Обработка callback для топ облигаций.

    Args:
        callback: Callback запрос от inline-кнопки

    Returns:
        None
    """
    if callback.message:
        await callback.answer()
        await _handle_top_bonds(callback.message, count=None)


@router.callback_query(F.data == "strategy_conservative")
async def callback_strategy_conservative(callback: CallbackQuery) -> None:
    """Обработка callback для консервативной стратегии.

    Args:
        callback: Callback запрос от inline-кнопки

    Returns:
        None
    """
    if callback.message:
        await callback.answer()
        await _handle_conservative_bonds(callback.message, count=None)


@router.callback_query(F.data == "strategy_high_yield")
async def callback_strategy_high_yield(callback: CallbackQuery) -> None:
    """Обработка callback для высокодоходной стратегии.

    Args:
        callback: Callback запрос от inline-кнопки

    Returns:
        None
    """
    if callback.message:
        await callback.answer()
        await _handle_high_yield_bonds(callback.message, count=None)
