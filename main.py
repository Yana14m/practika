import asyncio
import logging

from src.bot.bot import create_bot, create_dispatcher
from src.db.database import init_db
from src.notifications.notifications import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Инициализация БД...")
    init_db()

    bot = create_bot()
    dp = create_dispatcher()

    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планировщик запущен.")

    logger.info("Запуск бота...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
