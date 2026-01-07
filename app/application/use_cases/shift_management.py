from datetime import datetime

from app.domain.repositories import WorkerRepository, ShiftRepository


def detect_shift_type(hour: int) -> str | None:
    if 8 <= hour < 14:
        return "morning"
    if 14 <= hour < 20:
        return "evening"
    return None


class ShiftService:
    def __init__(self, workers: WorkerRepository, shifts: ShiftRepository):
        self.workers = workers
        self.shifts = shifts

    async def get_worker(self, chat_id: int):
        return await self.workers.get_by_chat_id(chat_id)

    async def get_worker_by_id(self, worker_id: int):
        return await self.workers.get_by_id(worker_id)

    async def list_all_doctors(self):
        return await self.workers.list_all()

    async def get_current_shift(self, worker_id: int, date: str, shift_type: str):
        return await self.shifts.get_for_assistant(worker_id, date, shift_type)

    async def list_free_shifts(self, date: str, shift_type: str):
        return await self.shifts.list_free(date, shift_type)

    async def add_shift_by_id(self, worker_id: int, worker_name: str, shift_id: int) -> bool:
        return await self.shifts.add_by_id(worker_id, worker_name, shift_id)

    async def remove_shift(self, assistant_id: int, date: str, shift_type: str) -> None:
        await self.shifts.remove_assistant(assistant_id, date, shift_type)

    async def add_manual_shift(
        self,
        assistant_id: int,
        assistant_name: str,
        doctor_name: str,
        shift_type: str,
        date: str,
    ) -> bool:
        return await self.shifts.add_manual(
            assistant_id, assistant_name, doctor_name, shift_type, date
        )

    async def get_shift_by_id(self, shift_id: int):
        return await self.shifts.get_by_id(shift_id)

    def guess_shift_type_from_now(self) -> tuple[str | None, str]:
        now = datetime.now()
        shift_type = detect_shift_type(now.hour)
        date_str = now.strftime("%d.%m.%Y")
        return shift_type, date_str
