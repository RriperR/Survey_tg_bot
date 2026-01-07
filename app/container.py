from app.config import load_settings
from app.infrastructure.db.repositories import (
    SqlAlchemyWorkerRepository,
    SqlAlchemyPairRepository,
    SqlAlchemySurveyRepository,
    SqlAlchemyAnswerRepository,
    SqlAlchemyShiftRepository,
)
from app.infrastructure.sheets.gateway import SheetsGateway
from app.application.use_cases.registration import RegistrationService
from app.application.use_cases.survey_flow import SurveyFlowService
from app.application.use_cases.shift_management import ShiftService
from app.application.use_cases.admin_sync import AdminSyncService
from app.application.use_cases.reports import ReportsService
from app.application.use_cases.scheduler import SurveyScheduler


class Container:
    def __init__(self):
        self.settings = load_settings()

        # Infrastructure
        self.worker_repo = SqlAlchemyWorkerRepository()
        self.pair_repo = SqlAlchemyPairRepository()
        self.survey_repo = SqlAlchemySurveyRepository()
        self.answer_repo = SqlAlchemyAnswerRepository()
        self.shift_repo = SqlAlchemyShiftRepository()

        self.sheets_gateway = SheetsGateway(self.settings.sheets)

        # Application layer
        self.registration = RegistrationService(self.worker_repo)
        self.survey_flow = SurveyFlowService(
            self.worker_repo,
            self.pair_repo,
            self.survey_repo,
            self.answer_repo,
        )
        self.shift_service = ShiftService(self.worker_repo, self.shift_repo)
        self.admin_sync = AdminSyncService(
            self.sheets_gateway,
            self.worker_repo,
            self.pair_repo,
            self.survey_repo,
            self.answer_repo,
            self.shift_repo,
        )
        self.reports = ReportsService(
            self.worker_repo,
            self.survey_repo,
            self.answer_repo,
            self.shift_repo,
        )
        self.scheduler = SurveyScheduler(self.survey_flow)


def build_container() -> Container:
    return Container()