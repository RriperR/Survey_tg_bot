from collections import defaultdict
from datetime import datetime

from aiogram import Bot, Dispatcher

from database import requests as rq
from handlers.survey_handlers import ask_next_question
from database.models import  Pair


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

        await start_pair_survey(bot, dp, int(worker.chat_id), first_pair)


async def start_pair_survey(bot: Bot, dp: Dispatcher, chat_id: int, pair: Pair):
    # 1. вступление
    await bot.send_message(
        chat_id,
        text=(
            f"{pair.date} с вами работал(-а): {pair.object}.\n"
            f"Пожалуйста, пройдите опрос: {pair.survey}"
        )
    )

    # 2. FSM
    state = dp.fsm.get_context(bot, chat_id, chat_id)
    survey = await rq.get_survey_by_name(pair.survey)

    await ask_next_question(
        bot=bot,
        user_id=chat_id,
        survey=survey,
        pair=pair,
        question_index=1,
        state=state,
    )
