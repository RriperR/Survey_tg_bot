# Q_tg_bot Architecture (DDD/Clean sketch)

## Layers
- `app/domain` – repository contracts that describe what the core needs (no framework calls).
- `app/application/use_cases` – orchestrate workflows (registration, surveys, shifts, admin sync, reports, scheduler).
- `app/infrastructure` – IO adapters:
  - `db/repositories.py` (SQLAlchemy implementations on `app.database.models`)
  - `sheets/gateway.py` (Google Sheets via gspread)
- `app/presentation` – aiogram routers in `app/handlers` plus keyboards.
- `app/container.py` – wires dependencies; `app/config.py` loads env/state; `app/logger.py` sets rotating file logging.

## Entry point
- Run: `python -m app.bot`
- Bot wiring: builds container, registers routers, starts scheduler (pairs/shifts sync, surveys, exports, monthly reports).

## Key flows
- **Registration**: `RegistrationService` + `register_handlers` (list unregistered workers, confirm, attach badge photo).
- **Surveys**: `SurveyFlowService` with `survey_handlers` FSM; `SurveyScheduler` triggers daily send, routes to next pair when finished.
- **Shifts**: `ShiftService` + `shift_handlers` for automatic/manual booking and cancel.
- **Admin**: `AdminSyncService` for Google Sheets sync/import/export commands.
- **Reports**: `ReportsService` builds monthly digests for workers.

## Notes
- Google credentials/key paths and sheet names come from `.env` (see `app/config.py`).
- Handlers are now English-only to avoid encoding issues; adjust texts as needed.***
