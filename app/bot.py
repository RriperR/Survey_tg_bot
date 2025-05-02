import os
import asyncio
import logging

from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers.register_handlers import router as register_router
from handlers.survey_handlers import router as survey_router
from handlers.admin_handlers import router as admin_router

from database.models import async_main
from services.reports import send_monthly_reports
from services.survey_reset import reset_surveys_and_notify_users
from services.survey_scheduler import send_surveys
from utils import update_pairs_from_sheet, export_answers_to_google_sheet


def init_logging():
    os.makedirs("logs", exist_ok=True)

    # Сброс всех старых хендлеров root-логгера
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    file_handler = TimedRotatingFileHandler(
        filename="logs/bot.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler]
    )

async def main():
    load_dotenv()
    init_logging()

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()

    await async_main()

    dp.include_router(admin_router)
    dp.include_router(register_router)
    dp.include_router(survey_router)

    # await send_monthly_reports(bot)
    await reset_surveys_and_notify_users(bot)
    await send_surveys(bot, dp)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_pairs_from_sheet, 'cron', hour=19, minute=50)
    scheduler.add_job(send_surveys, 'cron', hour=20, minute=0, args=[bot, dp])
    scheduler.add_job(export_answers_to_google_sheet, 'cron', day_of_week='sun', hour=23, minute=0)
    scheduler.add_job(send_monthly_reports, 'cron', day=1, hour=16, minute=38, args=[bot])
    scheduler.start()

    logging.info(f"Scheduler started with jobs: {scheduler.get_jobs()}")

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown")
