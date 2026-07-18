import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from obabot.proxy.bot import ProxyBot

from config import settings
from src.db.database import get_users_for_notification, mark_notification_sent

logger = logging.getLogger(__name__)


async def check_and_notify(bot: ProxyBot) -> None:
    logger.info("Проверка уведомлений...")
    notifications = get_users_for_notification(days=settings.NOTIFY_DAYS_BEFORE)

    if not notifications:
        logger.info("Нет заданий для уведомления.")
        return

    logger.info(f"Найдено {len(notifications)} заданий для уведомления.")

    for item in notifications:
        user_id = int(item["telegram_id"])
        assignment_id = item["assignment_id"]
        title = item["title"]
        deadline = item["deadline"]
        discipline = item["discipline_name"]

        try:
            dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
            deadline_readable = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            deadline_readable = deadline

        text = (
            f"⚠️ Напоминание о дедлайне!\n\n"
            f"📚 Дисциплина: {discipline}\n"
            f"📝 Задание: {title}\n"
            f"🕒 Срок сдачи: {deadline_readable}\n\n"
            f"Осталось меньше {settings.NOTIFY_DAYS_BEFORE} дн.!"
        )

        try:
            await bot.send_message(user_id, text)
            mark_notification_sent(assignment_id)
            logger.info(f"Уведомление отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")


def setup_scheduler(bot: ProxyBot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        check_and_notify,
        args=[bot],
        trigger=IntervalTrigger(minutes=settings.CHECK_INTERVAL_MINUTES),
        id="notify_job",
        replace_existing=True,
    )
    logger.info(
        f"Планировщик настроен: каждые {settings.CHECK_INTERVAL_MINUTES} мин., "
        f"за {settings.NOTIFY_DAYS_BEFORE} дн. до дедлайна."
    )
    return scheduler
