from sqlalchemy import select, update
from database.models import async_session
from database.models import Worker, Pair, Survey, Answer


async def get_worker_by_fullname(full_name: str):
    async with async_session() as session:
        stmt = select(Worker).where(Worker.full_name == full_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_worker_by_id(worker_id: int) -> Worker:
    async with async_session() as session:
        stmt = select(Worker).where(Worker.id == worker_id)
        result = await session.execute(stmt)
        return result.scalar()


async def get_unregistered_workers() -> list[Worker]:
    print("starting get_unregistered_workers()")
    async with async_session() as session:
        stmt = select(Worker).where(
            (Worker.chat_id.is_(None)) | (Worker.chat_id == '')
        )
        result = await session.execute(stmt)
        workers = result.scalars().all()
        return workers
    print("success get_unregistered_workers()")


async def set_chat_id(worker_id: int, chat_id: str) -> bool:
    async with async_session() as session:
        # Проверка: не используется ли chat_id уже
        existing_stmt = select(Worker).where(Worker.chat_id == chat_id)
        result = await session.execute(existing_stmt)
        existing = result.scalar_one_or_none()
        print(f"существующий работник:{existing}")
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


async def get_pairs_by_date(date: str) -> list[Pair]:
    """
    Вернёт все Pair, у которых поле date == date (формат 'dd.MM.YYYY').
    """
    async with async_session() as session:
        stmt = select(Pair).where(Pair.date == date)
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_survey_by_name(survey_name: str):
    """
    Найдёт объект Survey по его имени (survey_name).
    """
    async with async_session() as session:
        stmt = select(Survey).where(Survey.speciality == survey_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def save_answer(answer: Answer) -> None:
    """
    Запишет заполнённый Answer в БД.
    """
    async with async_session() as session:
        session.add(answer)
        await session.commit()