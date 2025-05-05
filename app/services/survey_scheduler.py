from collections import defaultdict
from datetime import datetime

from aiogram import Bot, Dispatcher

from database import requests as rq

from database.models import Pair
from handlers.survey_handlers import start_pair_survey
from logger import setup_logger

logger = setup_logger("surveys", "surveys.log")

async def send_surveys(bot: Bot, dp: Dispatcher) -> None:
    logger.info("📤 Запуск рассылки опросов")
    await rq.reset_incomplete_surveys()

    today = datetime.now().strftime('%d.%m.%Y')
    pairs = await rq.get_ready_pairs_by_date(today)

    # сгруппируем по пользователю
    by_user: dict[str, list[Pair]] = defaultdict(list)

    for p in pairs:
        by_user[p.subject].append(p)

    for subject, user_pairs in by_user.items():
        try:
            worker = await rq.get_worker_by_fullname(subject)
        except Exception as e:
            logger.error(f"get_worker_by_fullname: {e}. subject: {subject}.")

        if not worker or not worker.chat_id:
            logger.warning(f"Не удалось найти chat_id для {subject}")
            continue

        # проверяем, нет ли активного опроса
        if any(p.status == "in_progress" for p in user_pairs):
            logger.warning(f"Для {subject} уже есть активный опрос")
            continue                   # дождёмся его окончания

        pair = user_pairs[0]     # берём ровно один

        try:
            # Помечаем «в работе»
            await rq.update_pair_status(pair.id, "in_progress")

            file_id = await rq.get_file_id_by_name(pair.object)

            await start_pair_survey(bot, int(worker.chat_id), pair, dp=dp, file_id=file_id)
            logger.info(f"Отправлен опрос для {pair.subject} от {pair.date}, id: {pair.id}")
        except Exception as e:
            logger.error(f"Failed to start pair survey: {e}. id: {pair.id}")
