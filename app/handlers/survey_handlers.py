from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

import database.requests as rq
from database.models import Answer, Survey, Pair

from keyboards import build_int_keyboard


router = Router()

class SurveyState(StatesGroup):
    survey = State()
    pair   = State()
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()


async def ask_next_question(bot, user_id: int, survey: Survey, pair: Pair, question_index: int, state: FSMContext):
    """
    Запускает FSM-состояние для question_index (1..5),
    отправляет вопрос и сохраняет в state данные.
    """
    # заполняем общие данные при первом вопросе
    if question_index == 1:
        await state.update_data(
            survey=survey,
            pair=pair,
        )

    # готовим текст и тип
    q_text = getattr(survey, f"question{question_index}")
    q_type = getattr(survey, f"question{question_index}_type")

    # меняем state на следующее
    next_state = getattr(SurveyState, f"q{question_index}")
    await state.set_state(next_state)

    # отправляем вопрос
    if q_type == "int":
        # inline‑кнопки 1–5
        await bot.send_message(chat_id=user_id, text=q_text, reply_markup=await build_int_keyboard())
    else:
        # ждём текст
        await bot.send_message(chat_id=user_id, text=q_text)




# Обработчик для рейтинговых вопросов (inline)
@router.callback_query(StateFilter(SurveyState), F.data.startswith("rate:"))
async def handle_rate(callback: CallbackQuery, state: FSMContext):
    rate = callback.data.split(":",1)[1]
    data = await state.get_data()
    # определяем, в каком состоянии мы были
    current = await state.get_state()  # например 'SurveyState:q2'
    idx = int(current.split(":")[-1][1])  # из 'q2' -> 2

    # сохраняем ответ
    await state.update_data({f"q{idx}": rate})

    # отправим подтверждение (чтобы inline‑кнопка не крутилась)
    await callback.answer(f"Вы выбрали: {rate}")

    # переходим к следующему вопросу
    await ask_next_question(bot=callback.bot, user_id=callback.from_user.id,
                            survey=data["survey"],
                            pair=data["pair"],
                            question_index=idx+1,
                            state=state)


# Обработчик для текстовых вопросов
@router.message(StateFilter(SurveyState))
async def handle_text_answer(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        current = await state.get_state()  # 'SurveyState:qX'
        idx = int(current.split(":")[-1][1])

        # сохраняем текстовый ответ
        await state.update_data({f"q{idx}": message.text})

    except Exception as e:
        await message.answer(f"❗ Ошибка: {e}")
        raise

    # следующий вопрос или завершение
    if idx < 5:
        survey = data["survey"]
        pair = data["pair"]
        await ask_next_question(bot=message.bot, user_id=message.from_user.id,
                                survey=survey, pair=pair,
                                question_index=idx+1, state=state)
    else:
        answers = await state.get_data()
        survey = answers["survey"]
        pair = answers["pair"]

        ans = Answer(
            subject=pair.subject,
            object=pair.object,
            survey=pair.survey,
            survey_date=pair.date,
            completed_at=str(datetime.now()),
            question1=survey.question1,
            answer1=answers["q1"],
            question2=survey.question2,
            answer2=answers["q2"],
            question3=survey.question3,
            answer3=answers["q3"],
            question4=survey.question4,
            answer4=answers["q4"],
            question5=survey.question5,
            answer5=answers["q5"],
        )
        await rq.save_answer(ans)

        # сохранён ответ ...
        await rq.update_pair_status(pair.id, "done")  # 1. отмечаем завершение

        await state.clear()

        # 2. проверяем, есть ли ещё ready‑опросы для этого же subject
        next_pair = await rq.get_next_ready_pair(pair.subject)
        if next_pair:
            from services.survey_scheduler import send_surveys
            from bot import dp

            await rq.update_pair_status(next_pair.id, "in_progress")
            await send_surveys(message.bot, dp)
        else:
            await message.answer("Спасибо, опросы на сегодня закончились!")

