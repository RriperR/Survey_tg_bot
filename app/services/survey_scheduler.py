from collections import defaultdict
from datetime import datetime

from aiogram import Bot, Dispatcher

from database import requests as rq

from database.models import Pair
from handlers.survey_handlers import start_pair_survey


async def send_surveys(bot: Bot, dp: Dispatcher):
    await rq.reset_incomplete_surveys()

    today = datetime.now().strftime('%d.%m.%Y')
    pairs = await rq.get_ready_pairs_by_date(today)

    # сгруппируем по пользователю
    by_user: dict[str, list[Pair]] = defaultdict(list)
    for p in pairs:
        by_user[p.subject].append(p)

    for subject, user_pairs in by_user.items():
        worker = await rq.get_worker_by_fullname(subject)
        if not worker or not worker.chat_id:
            continue

        # проверяем, нет ли активного опроса
        if any(p.status == "in_progress" for p in user_pairs):
            continue                   # дождёмся его окончания

        first_pair = user_pairs[0]     # берём ровно один

        # Помечаем «в работе»
        await rq.update_pair_status(first_pair.id, "in_progress")

        await start_pair_survey(bot, int(worker.chat_id), first_pair, dp=dp)

