from app.domain.repositories import WorkerRepository
from app.database.models import Worker


class RegistrationService:
    def __init__(self, workers: WorkerRepository):
        self.workers = workers

    async def list_unregistered(self) -> list[Worker]:
        return list(await self.workers.list_unregistered())

    async def set_chat_id(self, worker_id: int, chat_id: str) -> bool:
        return await self.workers.set_chat_id(worker_id, chat_id)

    async def set_worker_photo(self, worker_id: int, file_id: str) -> None:
        await self.workers.set_file_id(worker_id, file_id)

    async def get_by_chat_id(self, chat_id: int) -> Worker | None:
        return await self.workers.get_by_chat_id(chat_id)

    async def get_by_id(self, worker_id: int) -> Worker | None:
        return await self.workers.get_by_id(worker_id)
