import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработка команды /start.

    Args:
        message: Входящее сообщение
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    logger.debug(f"Текст сообщения: {message.text}")

    welcome_text = (
        "👋 <b>Добро пожаловать в MOEX Bond Screener!</b>\n\n"
        "Этот бот поможет найти самые доходные надежные облигации на Московской Бирже.\n\n"
        "📊 <b>Доступные стратегии:</b>\n\n"
        "🔍 <b>Недооцененные ОФЗ</b>\n"
        "Поиск недооцененных облигаций в госсекторе\n\n"
        "🛡️ <b>Консервативная</b>\n"
        "ОФЗ и квазигосударственные, рейтинг ≥BBB, дюрация ≤4 года\n\n"
        "🚀 <b>Высокодоходная</b>\n"
        "Доходность >13%, рейтинг A/BBB, купон ежеквартально\n\n"
        "💡 <b>Режимы торгов:</b> TQCB (Корпоративные) + TQOB (ОФЗ)\n\n"
        "Выберите стратегию из меню ниже:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Топ облигации", callback_data="strategy_top")],
            [InlineKeyboardButton(text="🛡️ Консервативная", callback_data="strategy_conservative")],
            [InlineKeyboardButton(text="🚀 Высокодоходная", callback_data="strategy_high_yield")],
        ]
    )

    await message.answer(welcome_text, reply_markup=keyboard)
