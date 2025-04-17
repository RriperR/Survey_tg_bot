import os
from dotenv import load_dotenv
import asyncio
import logging

from aiogram import Bot, Dispatcher

from middlewares.logger import GroupLoggerMiddleware
from handlers import router
from database.models import async_main

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


async def main():
    await async_main()
    dp.include_router(router)
    dp.message.middleware(GroupLoggerMiddleware())
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown")


# from apscheduler.schedulers.background import BackgroundScheduler
#
# # Настройка планировщика
# scheduler = BackgroundScheduler()
#
# # Функции для запуска планировщика
# scheduler.add_job(update_local_cache, 'cron', hour=19, minute=50)
#
# scheduler.add_job(run_survey_dispatch, 'cron', hour=20, minute=30)
#
# scheduler.add_job(send_monthly_report, 'cron', day=4, hour=20, minute=52)
#
# scheduler.start()

