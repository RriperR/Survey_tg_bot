from sqlalchemy import select, update, delete

from database.models import async_session
from database.models import (
    Worker,
    Pair,
    Survey,
    Answer,
    Shift,
)


async def get_worker_by_fullname(full_name: str) -> Worker | None:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.full_name == full_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_worker_by_chat_id(chat_id: int) -> Worker | None:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.chat_id == str(chat_id))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_worker_by_id(worker_id: int) -> Worker:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.id == worker_id)
        result = await session.execute(stmt)
        return result.scalar()


async def get_unregistered_workers() -> list[Worker]:
    async with async_session() as session:
        stmt = select(Worker).where(
            (Worker.chat_id.is_(None)) | (Worker.chat_id == '')
        )
        result = await session.execute(stmt)
        workers = result.scalars().all()
        return workers


async def set_chat_id(worker_id: int, chat_id: str) -> bool:
    async with async_session() as session:
        # Проверка: не используется ли chat_id уже
        existing_stmt = select(Worker).where(Worker.chat_id == chat_id)
        result = await session.execute(existing_stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return False  # Уже зарегистрирован

        # Обновляем chat_id
        stmt = (
            update(Worker)
            .where(Worker.id == worker_id)
            .values(chat_id=chat_id)
        )
        await session.execute(stmt)
        await session.commit()
        return True


async def set_worker_file_id(worker_id: int, file_id: str) -> None:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.id == worker_id)
        result = await session.execute(stmt)
        worker = result.scalar_one_or_none()

        if worker:
            worker.file_id = file_id
            await session.commit()


async def get_survey_by_name(survey_name: str) -> Survey | None:
    """
    Найдёт объект Survey по его имени (survey_name).
    """
    async with async_session() as session:
        stmt = select(Survey).where(Survey.speciality == survey_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_ready_pairs_by_date(date: str) -> list[Pair]:
    async with async_session() as session:
        stmt = (
            select(Pair)
            .where(Pair.status == "ready", Pair.date <= date)
            .order_by(Pair.id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()


async def update_pair_status(pair_id: int, status: str) -> None:
    """
    Устанавливает новое значение поля Pair.status.
    """
    async with async_session() as session:
        stmt = (
            update(Pair)
            .where(Pair.id == pair_id)
            .values(status=status)
        )
        await session.execute(stmt)
        await session.commit()


async def reset_incomplete_surveys() -> None:
    """
    Все пары со статусом 'in_progress' → 'ready'
    """
    async with async_session() as session:
        stmt = (
            update(Pair)
            .where(Pair.status == "in_progress")
            .values(status="ready")
        )
        await session.execute(stmt)
        await session.commit()


async def get_next_ready_pair(subject: str) -> Pair | None:
    """
    Первый Pair со status='ready' для данного сотрудника (subject),
    упорядочен по id — чтобы сохранять тот же порядок, что и в send_surveys().
    """
    async with async_session() as session:
        stmt = (
            select(Pair)
            .where(Pair.subject == subject, Pair.status == "ready")
            .order_by(Pair.id)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def save_answer(answer: Answer) -> None:
    """
    Запишет заполнённый Answer в БД.
    """
    async with async_session() as session:
        session.add(answer)
        await session.commit()


async def get_file_id_by_name(name: str) -> str | None:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.full_name == name)
        result = await session.execute(stmt)
        worker = result.scalar_one_or_none()

        if worker and worker.file_id:
            return worker.file_id
        return None


async def get_all_answers() -> list[Answer]:
    async with async_session() as session:
        result = await session.execute(select(Answer))
        return result.scalars().all()

async def get_in_progress_pairs() -> list[Pair]:
    """
    Все пары, которые находятся в процессе заполнения.
    """
    async with async_session() as session:
        stmt = select(Pair).where(Pair.status == "in_progress")
        result = await session.execute(stmt)
        return result.scalars().all()


async def add_shift(assistant_id: int, assistant_name: str, doctor_name: str,
                    shift_type: str, date: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(Shift).where(
                Shift.doctor_name == doctor_name,
                Shift.date == date,
                Shift.type == shift_type,
            )
        )
        shift = result.scalar_one_or_none()
        if not shift or shift.assistant_id is not None:
            return False

        shift.assistant_id = assistant_id
        shift.assistant_name = assistant_name
        await session.commit()
        return True


async def clear_shifts() -> None:
    async with async_session() as session:
        await session.execute(delete(Shift))
        await session.commit()


async def bulk_insert_shifts(records: list[tuple[str, str, str]]) -> None:
    async with async_session() as session:
        for doctor_name, date, shift_type in records:
            session.add(
                Shift(
                    doctor_name=doctor_name,
                    date=date,
                    type=shift_type,
                )
            )
        await session.commit()


async def get_free_doctors(date: str, shift_type: str) -> list[str]:
    async with async_session() as session:
        result = await session.execute(
            select(Shift.doctor_name).where(
                Shift.date == date,
                Shift.type == shift_type,
                Shift.assistant_id.is_(None),
            )
        )
        return [row[0] for row in result.all()]
