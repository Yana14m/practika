import asyncio
import logging
from datetime import datetime

import obabot
from obabot.filters import Command, F
from obabot.types import InlineKeyboardButton, InlineKeyboardMarkup

import src.db.database as db
from config import settings
from src.guap_parser import auth
from src.guap_parser import parser as guap_parser

logger = logging.getLogger(__name__)

_bot, _dp, _router = obabot.create_bot(max_token=settings.BOT_TOKEN)


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Мои задания", callback_data="show_assignments"
                ),
                InlineKeyboardButton(
                    text="⏰ Дедлайны", callback_data="show_deadlines"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Синхронизировать ЛК", callback_data="sync_guap"
                )
            ],
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="show_profile"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="show_help"),
            ],
        ]
    )


MAX_MSG_LEN = 3900


async def send_long(message, text: str) -> None:
    """Разбивает текст на куски ≤ MAX_MSG_LEN и шлёт по очереди."""
    while text:
        chunk, text = text[:MAX_MSG_LEN], text[MAX_MSG_LEN:]
        await message.answer(chunk)


def normalize_deadline(raw_deadline: str) -> str:
    if not raw_deadline or not raw_deadline.strip():
        return "2099-12-31 23:59:00"
    cleaned = raw_deadline.strip()
    try:
        if len(cleaned) > 10:
            dt = datetime.strptime(cleaned, "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(cleaned, "%d.%m.%Y")
            dt = dt.replace(hour=23, minute=59, second=0)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return cleaned


# ── Команды ──────────────────────────────────────────────────────────────────


@_router.message(Command("start"))
async def cmd_start(message):
    tg_id = str(message.from_user.id)
    user = db.get_user(tg_id)
    if user is None:
        db.add_user(tg_id)
        text = (
            f"Привет, {message.from_user.first_name}! 👋\n"
            f"Я помогу следить за дедлайнами из ЛК ГУАП.\n\n"
            f"Нажми 👤 Профиль и привяжи логин и пароль."
        )
    else:
        text = f"С возвращением, {message.from_user.first_name}!"
    await message.answer(text, reply_markup=get_main_menu())


@_router.message(Command("set_password"))
async def cmd_set_password(message):
    tg_id = str(message.from_user.id)
    try:
        new_password = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        await message.answer("Формат: /set_password новый_пароль")
        return
    if db.update_user_password(tg_id, new_password):
        await message.answer("✅ Пароль обновлён.")
    else:
        await message.answer("❌ Ошибка. Сначала /start.")


@_router.message(F.text.contains(":"))
async def handle_credentials(message):
    tg_id = str(message.from_user.id)
    parts = message.text.split(":", 1)
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        await message.answer("❌ Формат: логин:пароль")
        return
    login_val = parts[0].strip()
    password_val = parts[1].strip()
    db.add_user(tg_id)
    if db.update_user_credentials(tg_id, login_val, password_val):
        await message.answer(
            f"✅ Данные сохранены!\n\n"
            f"👤 Логин: {login_val}\n"
            f"Нажми кнопку 🔄 Синхронизировать ЛК.",
        )
    else:
        await message.answer("❌ Ошибка базы данных.")


# ── Callback-кнопки ───────────────────────────────────────────────────────────


@_router.callback_query(F.data == "show_profile")
async def cb_show_profile(callback):
    tg_id = str(callback.from_user.id)
    user = db.get_user(tg_id)
    if not user:
        await callback.message.answer("Сначала /start")
        await callback.answer()
        return
    login_status = user["login"] if user["login"] else "не указан"
    pass_status = "сохранён ✅" if user["password"] else "не указан ❌"
    text = (
        f"👤 Профиль:\n\n"
        f"Логин ГУАП: {login_status}\n"
        f"Пароль: {pass_status}\n\n"
        f"Для привязки отправь сообщение: логин:пароль"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Удалить аккаунт 🗑", callback_data="delete_account"
                )
            ],
            [InlineKeyboardButton(text="← Назад", callback_data="show_menu")],
        ]
    )
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@_router.callback_query(F.data == "show_assignments")
async def cb_show_assignments(callback):
    tg_id = str(callback.from_user.id)
    user = db.get_user(tg_id)
    if not user:
        await callback.message.answer("Сначала /start")
        await callback.answer()
        return
    assignments = db.get_assignments(user["id"])
    if not assignments:
        await callback.message.answer("Список пуст. Нажми 🔄 Синхронизировать ЛК.")
        await callback.answer()
        return
    text = "📋 Задания из ГУАП:\n\n"
    for i, ass in enumerate(assignments, 1):
        emoji = "✅" if ass["status"] == "принят" else "⏳"
        text += (
            f"{i}. {emoji} {ass['discipline_name']}\n"
            f"   🔹 {ass['title']}\n"
            f"   📅 {ass['deadline']}\n\n"
        )
    await send_long(callback.message, text)
    await callback.answer()


@_router.callback_query(F.data == "show_deadlines")
async def cb_show_deadlines(callback):
    tg_id = str(callback.from_user.id)
    user = db.get_user(tg_id)
    if not user:
        await callback.message.answer("Сначала /start")
        await callback.answer()
        return
    soon = db.get_assignments_soon(user["id"], 3)
    if not soon:
        await callback.message.answer("🎉 Дедлайнов на ближайшие 3 дня нет!")
        await callback.answer()
        return
    text = "⚠️ Дедлайны на ближайшие 3 дня:\n\n"
    for ass in soon:
        text += f"🚨 {ass['discipline_name']}\n📌 {ass['title']}\n🕒 {ass['deadline']}\n\n"
    await send_long(callback.message, text)
    await callback.answer()


@_router.callback_query(F.data == "show_help")
async def cb_show_help(callback):
    text = (
        "❓ Справка:\n\n"
        "• Отправь логин:пароль для привязки аккаунта.\n"
        "• Кнопка 🔄 Синхронизировать ЛК скачает задания с pro.guap.ru.\n"
        "• /set_password <пароль> — сменить пароль."
    )
    await callback.message.answer(text)
    await callback.answer()


@_router.callback_query(F.data == "show_menu")
async def cb_show_menu(callback):
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()


@_router.callback_query(F.data == "sync_guap")
async def cb_sync_guap(callback):
    tg_id = str(callback.from_user.id)
    user = db.get_user(tg_id)
    if not user or not user["login"] or not user["password"]:
        await callback.message.answer(
            "❌ Сначала привяжи аккаунт — отправь логин:пароль"
        )
        await callback.answer()
        return
    await callback.message.answer("🔄 Подключаюсь к ЛК ГУАП...")
    await callback.answer()
    try:
        loop = asyncio.get_running_loop()
        session = await loop.run_in_executor(
            None, auth.login, user["login"], user["password"]
        )
        tasks = await loop.run_in_executor(None, guap_parser.get_tasks, session)
        if not tasks:
            await callback.message.answer("👍 Активных заданий не найдено.")
            return
        grouped: dict = {}
        for task in tasks:
            subject = task["subject"]
            if subject not in grouped:
                grouped[subject] = {
                    "name": subject,
                    "teacher": task["teacher"],
                    "assignments": [],
                }
            grouped[subject]["assignments"].append({
                "title": f"Задание №{task['number']}: {task['task']}",
                "deadline": normalize_deadline(task["deadline"]),
                "source_id": str(task["number"]),
            })
        result = db.sync_assignments(user["id"], list(grouped.values()))
        await callback.message.answer(
            f"✅ Синхронизация успешна!\n\n"
            f"➕ Новых: {result['added']}\n"
            f"🔄 Обновлено: {result['updated']}"
        )
    except Exception as e:
        logger.error(f"Ошибка синхронизации: {e}")
        await callback.message.answer("❌ Ошибка авторизации. Проверь данные.")


@_router.callback_query(F.data == "delete_account")
async def cb_delete_account(callback):
    tg_id = str(callback.from_user.id)
    if db.delete_user(tg_id):
        await callback.message.edit_text("Профиль деактивирован. Для возврата /start.")
        await callback.answer("Удалено")
    else:
        await callback.answer("Ошибка БД", show_alert=True)


# ── Экспорт для main.py ───────────────────────────────────────────────────────


def create_bot():
    return _bot


def create_dispatcher():
    return _dp
