from sqlalchemy import select, update, or_, func

from database.models import async_session
from database.models import Worker

async def get_worker_by_id(worker_id: int) -> Worker:
    print()
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
