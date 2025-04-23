import os
import asyncio
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from middlewares.logger import GroupLoggerMiddleware
from handlers.register_handlers import router as register_router
from handlers.survey_handlers import router as survey_router

from database.models import async_main
from services.survey_scheduler import send_surveys
from utils import update_pairs_from_sheet


load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()



async def main():
    await async_main()
    dp.include_router(register_router)
    dp.include_router(survey_router)

    await send_surveys(bot, dp)

    # # Планировщик
    # scheduler = AsyncIOScheduler()
    # scheduler.add_job(update_pairs_from_sheet, 'cron', hour=17, minute=5)
    # scheduler.add_job(send_surveys, 'cron', hour=17, minute=16, args=[bot, dp])
    # scheduler.start()
    # print(f"scheduler: {scheduler.get_jobs()}")

    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown")

