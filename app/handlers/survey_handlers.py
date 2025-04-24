from datetime import datetime

from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

import database.requests as rq
from database.models import Answer, Pair

from keyboards import build_int_keyboard

router = Router()

class SurveyState(StatesGroup):
    answers = State()


async def start_pair_survey(bot: Bot, chat_id: int, pair: Pair,
                            state: FSMContext = None, dp: Dispatcher = None, file_id: str = None) -> None:
    # 1. вступление
    if file_id:
        await bot.send_photo(
            chat_id=chat_id,
            photo=file_id,
            caption=(
            f"{pair.date} с вами работал(-а): {pair.object}.\n"
            f"Пожалуйста, пройдите опрос: {pair.survey}"
            )
        )

    else:
        await bot.send_message(
            chat_id,
            text=(
                f"{pair.date} с вами работал(-а): {pair.object}.\n"
                f"Пожалуйста, пройдите опрос: {pair.survey}"
            )
        )

    # 2. FSM
    if state is None:
        state = dp.fsm.get_context(bot, chat_id, chat_id)

    survey = await rq.get_survey_by_name(pair.survey)

    await state.update_data(survey=survey, pair=pair, answers=[])

    await ask_next_question(
        bot=bot,
        user_id=chat_id,
        question_index=1,
        state=state,
    )


async def ask_next_question(bot, user_id: int, question_index: int, state: FSMContext) -> None:
    # готовим текст и тип
    data = await state.get_data()
    survey = data.get("survey")

    q_text = getattr(survey, f"question{question_index}")
    q_type = getattr(survey, f"question{question_index}_type")


    # отправляем вопрос
    if q_type == "int":
        # inline‑кнопки 1–5
        await bot.send_message(chat_id=user_id, text=q_text, reply_markup=await build_int_keyboard(question_index))
    else:
        # ждём текст
        await state.set_state(SurveyState.answers)
        await bot.send_message(chat_id=user_id, text=q_text)


# Обработчик для рейтинговых вопросов (inline)
@router.callback_query(F.data.startswith("rate:"))
async def handle_rate(callback: CallbackQuery, state: FSMContext):
    _, question_index, rate, timestamp = callback.data.split(":")
    idx = int(question_index)

    created_time = datetime.fromtimestamp(int(timestamp))
    now = datetime.now()

    if (now - created_time).total_seconds() > 86400:  # 24 часа
        await callback.message.edit_text(text="Сообщение устарело", reply_markup=None)
        return

    # сохраняем ответ
    data = await state.get_data()
    answers: list = data.get("answers")
    if idx > 1 and len(answers) == 0:
        await callback.message.edit_text(text="Сообщение устарело", reply_markup=None)
        return

    answers.append(rate)

    await state.update_data(answers=answers)


    # отправим подтверждение (чтобы inline‑кнопка не крутилась)
    await callback.answer(f"Вы выбрали: {rate}")

    text = callback.message.text
    text += f"\n\n Вы поставили оценку {rate}"

    await callback.message.edit_text(text=text, reply_markup=None)


    # переходим к следующему вопросу
    await ask_next_question(bot=callback.bot, user_id=callback.from_user.id,
                            question_index=idx+1,
                            state=state)


# Обработчик для текстовых вопросов
@router.message(StateFilter(SurveyState.answers))
async def handle_text_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    answers: list = data.get("answers")
    answers.append(message.text)
    await state.update_data(answers=answers)

    idx = len(answers)


    # следующий вопрос или завершение
    if idx < 5:
        await ask_next_question(bot=message.bot, user_id=message.from_user.id,
                                question_index=idx+1, state=state)

    else:
        a1, a2, a3, a4, a5 = data.get("answers")
        pair = data.get("pair")
        survey = data.get("survey")

        ans = Answer(
            subject=pair.subject,
            object=pair.object,
            survey=pair.survey,
            survey_date=pair.date,
            completed_at=str(datetime.now()),
            question1=survey.question1,
            answer1=a1,
            question2=survey.question2,
            answer2=a2,
            question3=survey.question3,
            answer3=a3,
            question4=survey.question4,
            answer4=a4,
            question5=survey.question5,
            answer5=a5,
        )
        await rq.save_answer(ans)

        # сохранён ответ ...
        await rq.update_pair_status(pair.id, "done")  # 1. отмечаем завершение

        await state.clear()

        # 2. проверяем, есть ли ещё ready‑опросы для этого же subject
        next_pair = await rq.get_next_ready_pair(pair.subject)
        if next_pair:
            await rq.update_pair_status(next_pair.id, "in_progress")
            file_id = await rq.get_file_id_by_name(next_pair.object)
            await start_pair_survey(message.bot, message.from_user.id, next_pair, state = state, file_id=file_id)
        else:
            await message.answer("Спасибо, опросы на сегодня закончились!")

