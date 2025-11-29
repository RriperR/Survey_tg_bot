from sqlalchemy import select, update, delete

from app.database.models import (
    async_session,
    Worker,
    Pair,
    Survey,
    Answer,
    Shift,
)
from app.domain.repositories import (
    WorkerRepository,
    PairRepository,
    SurveyRepository,
    AnswerRepository,
    ShiftRepository,
)


class SqlAlchemyWorkerRepository(WorkerRepository):
    async def get_by_fullname(self, full_name: str) -> Worker | None:
        async with async_session() as session:
            stmt = select(Worker).where(Worker.full_name == full_name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> Worker | None:
        async with async_session() as session:
            stmt = select(Worker).where(Worker.chat_id == str(chat_id))
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_id(self, worker_id: int) -> Worker | None:
        async with async_session() as session:
            stmt = select(Worker).where(Worker.id == worker_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(select(Worker))
            return result.scalars().all()

    async def list_unregistered(self):
        async with async_session() as session:
            stmt = select(Worker).where(
                (Worker.chat_id.is_(None)) | (Worker.chat_id == "")
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def add(self, worker: Worker) -> None:
        async with async_session() as session:
            session.add(worker)
            await session.commit()

    async def set_chat_id(self, worker_id: int, chat_id: str) -> bool:
        async with async_session() as session:
            existing_stmt = select(Worker).where(Worker.chat_id == chat_id)
            result = await session.execute(existing_stmt)
            if result.scalar_one_or_none():
                return False

            stmt = (
                update(Worker)
                .where(Worker.id == worker_id)
                .values(chat_id=chat_id)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    async def set_file_id(self, worker_id: int, file_id: str) -> None:
        async with async_session() as session:
            worker = await session.get(Worker, worker_id)
            if worker:
                worker.file_id = file_id
                await session.commit()


class SqlAlchemySurveyRepository(SurveyRepository):
    async def get_by_name(self, name: str) -> Survey | None:
        async with async_session() as session:
            stmt = select(Survey).where(Survey.speciality == name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def clear_all(self) -> None:
        async with async_session() as session:
            await session.execute(delete(Survey))
            await session.commit()

    async def add(self, survey: Survey) -> None:
        async with async_session() as session:
            session.add(survey)
            await session.commit()


class SqlAlchemyPairRepository(PairRepository):
    async def list_ready_by_date(self, date: str):
        async with async_session() as session:
            stmt = (
                select(Pair)
                .where(Pair.status == "ready", Pair.date <= date)
                .order_by(Pair.id)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def next_ready_for_subject(self, subject: str) -> Pair | None:
        async with async_session() as session:
            stmt = (
                select(Pair)
                .where(Pair.subject == subject, Pair.status == "ready")
                .order_by(Pair.id)
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_status(self, pair_id: int, status: str) -> None:
        async with async_session() as session:
            stmt = (
                update(Pair)
                .where(Pair.id == pair_id)
                .values(status=status)
            )
            await session.execute(stmt)
            await session.commit()

    async def reset_incomplete(self) -> None:
        async with async_session() as session:
            stmt = (
                update(Pair)
                .where(Pair.status == "in_progress")
                .values(status="ready")
            )
            await session.execute(stmt)
            await session.commit()

    async def add(self, pair: Pair) -> None:
        async with async_session() as session:
            session.add(pair)
            await session.commit()

    async def clear_all(self) -> None:
        async with async_session() as session:
            await session.execute(delete(Pair))
            await session.commit()


class SqlAlchemyAnswerRepository(AnswerRepository):
    async def save(self, answer: Answer) -> None:
        async with async_session() as session:
            session.add(answer)
            await session.commit()

    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(select(Answer))
            return result.scalars().all()


class SqlAlchemyShiftRepository(ShiftRepository):
    async def clear_all(self) -> None:
        async with async_session() as session:
            await session.execute(delete(Shift))
            await session.commit()

    async def bulk_insert(self, records: list[tuple[str, str, str]]) -> None:
        async with async_session() as session:
            for doctor_name, date, shift_type in records:
                session.add(
                    Shift(
                        doctor_name=doctor_name,
                        date=date,
                        type=shift_type,
                        manual=False,
                    )
                )
            await session.commit()

    async def list_free(self, date: str, shift_type: str) -> list[tuple[int, str]]:
        async with async_session() as session:
            result = await session.execute(
                select(Shift.id, Shift.doctor_name).where(
                    Shift.date == date,
                    Shift.type == shift_type,
                    Shift.assistant_id.is_(None),
                )
            )
            return [(row.id, row.doctor_name) for row in result.all()]

    async def get_by_id(self, shift_id: int) -> Shift | None:
        async with async_session() as session:
            return await session.get(Shift, shift_id)

    async def get_for_assistant(self, assistant_id: int, date: str, shift_type: str) -> Shift | None:
        async with async_session() as session:
            result = await session.execute(
                select(Shift).where(
                    Shift.assistant_id == assistant_id,
                    Shift.date == date,
                    Shift.type == shift_type,
                )
            )
            return result.scalar_one_or_none()

    async def remove_assistant(self, assistant_id: int, date: str, shift_type: str) -> None:
        async with async_session() as session:
            stmt = (
                update(Shift)
                .where(
                    Shift.assistant_id == assistant_id,
                    Shift.date == date,
                    Shift.type == shift_type,
                )
                .values(assistant_id=None, assistant_name=None)
            )
            await session.execute(stmt)
            await session.commit()

    async def add_by_id(self, assistant_id: int, assistant_name: str, shift_id: int) -> bool:
        async with async_session() as session:
            shift = await session.get(Shift, shift_id)
            if not shift or shift.assistant_id is not None:
                return False

            already_stmt = await session.execute(
                select(Shift).where(
                    Shift.assistant_id == assistant_id,
                    Shift.date == shift.date,
                    Shift.type == shift.type,
                )
            )
            if already_stmt.scalar_one_or_none():
                return False

            shift.assistant_id = assistant_id
            shift.assistant_name = assistant_name
            shift.manual = False
            await session.commit()
            return True

    async def add_manual(
        self,
        assistant_id: int,
        assistant_name: str,
        doctor_name: str,
        shift_type: str,
        date: str,
    ) -> bool:
        async with async_session() as session:
            already = await session.execute(
                select(Shift).where(
                    Shift.assistant_id == assistant_id,
                    Shift.date == date,
                    Shift.type == shift_type,
                )
            )
            if already.scalar_one_or_none():
                return False

            shift = Shift(
                assistant_id=assistant_id,
                assistant_name=assistant_name,
                doctor_name=doctor_name,
                type=shift_type,
                date=date,
                manual=True,
            )
            session.add(shift)
            await session.commit()
            return True

    async def list_by_date(self, date: str):
        async with async_session() as session:
            result = await session.execute(
                select(Shift).where(Shift.date == date)
            )
            return result.scalars().all()

    async def list_all(self):
        async with async_session() as session:
            result = await session.execute(select(Shift))
            return result.scalars().all()
