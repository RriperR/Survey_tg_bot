from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

from aiogram import Bot

from sqlalchemy import select

from database.models import async_session, Answer, Worker, Survey, Shift
from logger import setup_logger

logger = setup_logger("reports", "reports.log")

def parse_russian_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").replace(tzinfo=ZoneInfo("Europe/Moscow"))
    except Exception:
        return None


async def _collect_survey_cache(session, all_answers: list[Answer]) -> dict[str, Survey]:
    survey_names = set(ans.survey for ans in all_answers)
    surveys_by_name = {}
    for name in survey_names:
        stmt = select(Survey).where(Survey.speciality == name)
        res = await session.execute(stmt)
        surveys_by_name[name] = res.scalar_one_or_none()
    return surveys_by_name


def _group_answers_by_object(all_answers: list[Answer]) -> dict[str, list[Answer]]:
    grouped = defaultdict(list)
    for ans in all_answers:
        grouped[ans.object].append(ans)
    return grouped


def _group_shifts_last_month(all_shifts: list[Shift], now: datetime) -> dict[int, dict[str, int]]:
    """Return mapping assistant_id -> {doctor_name: count} for last month."""
    one_month_ago = now - timedelta(days=30)
    result: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for shift in all_shifts:
        if shift.assistant_id is None:
            continue
        shift_date = parse_russian_date(shift.date)
        if not shift_date or shift_date < one_month_ago:
            continue
        result[shift.assistant_id][shift.doctor_name] += 1
    return result


def _calculate_scores_for_worker(
    answers: list[Answer],
    surveys_by_name: dict[str, Survey],
    now: datetime
) -> tuple[dict[str, dict[str, dict[str, list[int]]]], dict[str, list[str]]]:
    one_month_ago = now - timedelta(days=30)
    six_months_ago = now - timedelta(days=180)

    results = {
        "Месяц": defaultdict(lambda: defaultdict(list)),
        "Полгода": defaultdict(lambda: defaultdict(list)),
        "Всё время": defaultdict(lambda: defaultdict(list)),
    }

    open_answers = defaultdict(list)  # Открытые ответы (строки) за месяц

    for ans in answers:
        survey = surveys_by_name.get(ans.survey)
        if not survey:
            continue

        survey_date = parse_russian_date(ans.survey_date)
        if not survey_date:
            continue

        for i in range(1, 6):
            question_text = getattr(survey, f"question{i}", f"Вопрос {i}").split('\n')[0]
            q_type = getattr(survey, f"question{i}_type")

            raw_answer = getattr(ans, f"answer{i}")
            if q_type == "int":
                try:
                    score = int(raw_answer)
                    if not (1 <= score <= 5):
                        continue
                except (ValueError, TypeError):
                    continue

                if survey_date >= one_month_ago:
                    results["Месяц"][survey.speciality][question_text].append(score)
                if survey_date >= six_months_ago:
                    results["Полгода"][survey.speciality][question_text].append(score)
                results["Всё время"][survey.speciality][question_text].append(score)

            elif q_type == "str" and survey_date >= one_month_ago:
                if raw_answer and raw_answer.strip():
                    open_answers[survey.speciality].append((question_text, raw_answer.strip()))

    return results, open_answers


def _format_report_text(
    worker_name: str,
    results: dict[str, dict[str, dict[str, list[int]]]],
    open_answers: dict[str, list[str]],
    shifts_info: dict[str, int] | None = None,
) -> list[str]:
    messages: list[str] = []
    period_values_seen = set()

    for period_name, surveys in results.items():
        serialized = str(sorted((survey, question, sorted(scores))
                                 for survey, questions in surveys.items()
                                 for question, scores in questions.items()))

        has_scores = bool(surveys)
        has_month_extras = period_name == "Месяц" and (
            open_answers or shifts_info
        )
        if not has_scores and not has_month_extras:
            continue
        if has_scores and serialized in period_values_seen:
            continue
        if has_scores:
            period_values_seen.add(serialized)

        text = f"📊 Результаты за 📅 *{period_name}:*\n\n"

        for survey_title, questions in surveys.items():
            text += f"🔹 _Опрос:_ *{survey_title}*\n"
            for question, scores in questions.items():
                avg = round(sum(scores) / len(scores), 2)
                text += f"• {question}\n *{avg}* из 5 ({len(scores)} оценок)\n\n"

        # 👇 Вставляем рекомендации только в блок "Месяц"
        if period_name == "Месяц" and open_answers:
            text += f"📝 *Рекомендации:*\n"
            for survey_title, qa_pairs in open_answers.items():
                grouped: dict[str, list[str]] = defaultdict(list)
                for question, answer in qa_pairs:
                    grouped[question.strip()].append(answer.strip())

                text += f"\n_Опрос:_ *{survey_title}*\n"
                for question, answers in grouped.items():
                    text += f"• {question}\n"
                    for a in answers:
                        text += f"    - {a}\n"
                    text += "\n"

        if period_name == "Месяц" and shifts_info:
            text += "\n🩺 *Смены за последний месяц:*\n"
            for doctor, count in shifts_info.items():
                text += f"• {doctor} — {count} раз(а)\n"

        messages.append(text.strip())

    return messages


async def send_monthly_reports(bot: Bot):
    logger.info("📬 Начало рассылки результатов")
    now = datetime.now(ZoneInfo("Europe/Moscow"))

    async with async_session() as session:
        # Загружаем работников
        workers_result = await session.execute(select(Worker))
        workers = workers_result.scalars().all()
        logger.info(f"Найдено сотрудников: {len(workers)}")

        # Загружаем ответы
        answers_result = await session.execute(select(Answer))
        all_answers = answers_result.scalars().all()
        logger.info(f"Найдено ответов: {len(all_answers)}")

        shifts_result = await session.execute(select(Shift))
        all_shifts = shifts_result.scalars().all()
        logger.info(f"Найдено смен: {len(all_shifts)}")

        surveys_by_name = await _collect_survey_cache(session, all_answers)
        logger.info(f"Кэшировано опросов: {len(surveys_by_name)}")

        answers_by_object = _group_answers_by_object(all_answers)
        shifts_by_assistant = _group_shifts_last_month(all_shifts, now)

        sent_count = 0
        skipped_count = 0

        for worker in workers:
            worker_answers = answers_by_object.get(worker.full_name)
            if not worker_answers:
                skipped_count += 1
                logger.debug(f"Пропущен сотрудник без оценок: {worker.full_name}")
                continue

            results, open_answers = _calculate_scores_for_worker(
                worker_answers, surveys_by_name, now
            )

            worker_shifts = shifts_by_assistant.get(worker.id)

            try:
                messages = _format_report_text(
                    worker.full_name,
                    results,
                    open_answers,
                    worker_shifts,
                )
                for message in messages:
                    await safe_send_long_message(bot, worker.chat_id, message)
                logger.info(
                    f"✅ Отчёт отправлен: {worker.full_name} ({worker.chat_id})"
                )
                sent_count += 1
            except Exception as e:
                logger.error(
                    f"❌ Ошибка при отправке {worker.full_name} ({worker.chat_id}): {e}"
                )

        logger.info(f"📊 Рассылка завершена. Отправлено: {sent_count}, пропущено: {skipped_count}")


def split_message(text: str, max_len: int = 4096) -> list[str]:
    lines = text.split('\n')
    chunks = []
    current = ''
    for line in lines:
        if len(current) + len(line) + 1 < max_len:
            current += line + '\n'
        else:
            chunks.append(current.strip())
            current = line + '\n'
    if current:
        chunks.append(current.strip())
    return chunks

async def safe_send_long_message(bot: Bot, chat_id: str, text: str, parse_mode: str = "Markdown"):
    for part in split_message(text):
        await bot.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode)
