import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext

from middlewares.logger import GroupLoggerMiddleware
from handlers.register_handlers import router as register_router
from handlers.survey_handlers import router as survey_router

from database.models import async_main
from database.requests import get_pairs_by_date, get_survey_by_name, get_worker_by_fullname
from handlers.survey_handlers import ask_next_question


async def send_surveys(bot: Bot):
    print('sending surveys')
    today_str = datetime.now().strftime('%d.%m.%Y')
    pairs = await get_pairs_by_date(today_str)
    print(f'number of pairs: {len(pairs)}')

    for pair in pairs:
        worker = await get_worker_by_fullname(pair.subject)
        # если не нашли или нет chat_id — пропускаем
        if not worker or not worker.chat_id:
            continue

        chat_id = int(worker.chat_id)
        # 1) Вступительное сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"На этой неделе с вами работал(-а): {pair.object}.\n"
                f"Пожалуйста, пройдите опрос: {pair.survey}"
            )
        )

        # 2) Запускаем FSM для первого вопроса
        state: FSMContext = dp.fsm.get_context(bot, chat_id, chat_id)
        survey = await get_survey_by_name(pair.survey)

        # Передаём: survey_id, пары subject/object, все вопросы
        await ask_next_question(
            bot=bot,
            user_id=chat_id,
            survey=survey,
            pair=pair,
            question_index=1,
            state=state,
        )


load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


async def main():
    await async_main()
    dp.include_router(register_router)
    dp.include_router(survey_router)
    # dp.message.middleware(GroupLoggerMiddleware())
    await send_surveys(bot)
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

