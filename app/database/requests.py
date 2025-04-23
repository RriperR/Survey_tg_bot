from sqlalchemy import select, update
from typing import Optional

from database.models import async_session
from database.models import Worker, Pair, Survey, Answer


async def get_worker_by_fullname(full_name: str) -> Optional[Worker]:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.full_name == full_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_worker_by_chat_id(chat_id: int) -> Optional[Worker]:
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


async def get_survey_by_name(survey_name: str) -> Optional[Survey]:
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


async def get_next_ready_pair(subject: str) -> Optional[Pair]:
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


async def get_file_id_by_name(name: str) -> Optional[str]:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.full_name == name)
        result = await session.execute(stmt)
        worker = result.scalar_one_or_none()

        if worker and worker.file_id:
            return worker.file_id
        return None

