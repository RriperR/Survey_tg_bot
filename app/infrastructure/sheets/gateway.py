from pathlib import Path
from typing import Iterable

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from app.config import SheetsSettings


class SheetsGateway:
    """Thin wrapper over gspread to isolate IO with Google Sheets."""

    def __init__(self, settings: SheetsSettings):
        self.settings = settings
        self.client = self._build_client(settings.credentials_path)
        self.spreadsheet = self.client.open(settings.main_table) if settings.main_table else None
        self.answers_spreadsheet = self.client.open(settings.answers_table) if settings.answers_table else None

    def _build_client(self, credentials_path: Path) -> gspread.Client:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            str(credentials_path), scope
        )
        return gspread.authorize(creds)

    # --- Readers ---
    def read_workers(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.workers_sheet)
        return worksheet.get_all_values()[1:]

    def read_pairs(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.pairs_sheet)
        return worksheet.get_all_values()[1:]

    def read_surveys(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.surveys_sheet)
        return worksheet.get_all_values()[1:]

    def read_shifts(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.shifts_source_sheet)
        return worksheet.get_all_values()[1:]

    # --- Writers ---
    def export_answers(self, headers: list[str], rows: Iterable[list[str]]) -> None:
        worksheet = self._require_answers_sheet(self.settings.answers_sheet)
        worksheet.clear()
        worksheet.append_row(headers)
        if rows:
            worksheet.append_rows(list(rows), value_input_option="RAW")

    def export_shifts(self, headers: list[str], rows: Iterable[list[str]]) -> None:
        worksheet = self._require_answers_sheet(self.settings.shift_report_sheet)
        existing = worksheet.get_all_values()
        if not existing:
            worksheet.append_row(headers)
        if rows:
            worksheet.append_rows(list(rows), value_input_option="RAW")

    # --- Helpers ---
    def _require_main_sheet(self, name: str):
        if not self.spreadsheet:
            raise RuntimeError("Main spreadsheet is not configured (TABLE env missing)")
        return self.spreadsheet.worksheet(name)

    def _require_answers_sheet(self, name: str):
        if not self.answers_spreadsheet:
            raise RuntimeError("Answers spreadsheet is not configured (ANSWERS_TABLE env missing)")
        return self.answers_spreadsheet.worksheet(name)