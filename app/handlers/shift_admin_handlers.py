from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.use_cases.shift_admin import ShiftAdminService
from app.domain.entities import Shift, Worker
from app.logger import setup_logger


logger = setup_logger("shift_admin", "shift_admin.log")

PER_PAGE = 10


def create_shift_admin_router(
    shift_admin: ShiftAdminService,
    admin_chat_ids: set[str],
) -> Router:
    router = Router()

    def is_admin(user_id: int) -> bool:
        return str(user_id) in admin_chat_ids

    async def require_admin(target: Message | CallbackQuery) -> bool:
        user_id = target.from_user.id
        if not is_admin(user_id):
            if isinstance(target, CallbackQuery):
                await target.answer("Нет доступа", show_alert=True)
            else:
                await target.answer("Нет доступа")
            return False
        return True

    def format_shift(shift: Shift) -> str:
        shift_type = "Утренняя" if shift.type == "morning" else "Вечерняя"
        shift_emoji = "🌅" if shift.type == "morning" else "🌙"
        if shift.assistant_id:
            assistant = shift.assistant_name or str(shift.assistant_id)
            status = f"✅ занята: {assistant}"
        else:
            status = "🟢 свободна"
        manual = " ✋" if shift.manual else ""
        return f"{shift_emoji} {shift.id}) {shift_type} — {shift.doctor_name} — {status}{manual}"

    def build_shift_list_keyboard(shifts: list[Shift]):
        builder = InlineKeyboardBuilder()
        builder.button(text="Создать смену", callback_data="admin_shift_create")
        builder.button(text="Удалить смену", callback_data="admin_shift_delete_menu")
        builder.button(text="Обновить", callback_data="admin_shift_refresh")
        builder.button(text="К админке", callback_data="admin_back")
        builder.adjust(1)
        return builder.as_markup()

    def build_create_type_keyboard():
        builder = InlineKeyboardBuilder()
        builder.button(text="Утренняя", callback_data="admin_shift_create_type:morning")
        builder.button(text="Вечерняя", callback_data="admin_shift_create_type:evening")
        builder.button(text="Назад", callback_data="admin_shift_refresh")
        builder.adjust(1)
        return builder.as_markup()

    def build_doctors_keyboard(workers: list[Worker], shift_type: str, page: int):
        total = len(workers)
        start = page * PER_PAGE
        end = min(start + PER_PAGE, total)

        builder = InlineKeyboardBuilder()
        for w in workers[start:end]:
            builder.button(
                text=w.full_name[:64],
                callback_data=f"admin_shift_create_doctor:{shift_type}:{w.id}",
            )

        nav = InlineKeyboardBuilder()
        if start > 0:
            nav.button(
                text="Назад",
                callback_data=f"admin_shift_doctors:{shift_type}:{page - 1}",
            )
        if end < total:
            nav.button(
                text="Вперёд",
                callback_data=f"admin_shift_doctors:{shift_type}:{page + 1}",
            )
        if nav.buttons:
            builder.row(*nav.buttons)

        back_builder = InlineKeyboardBuilder()
        back_builder.button(text="К типу смены", callback_data="admin_shift_create")
        builder.row(*back_builder.buttons)
        return builder.as_markup()

    def build_delete_confirm_keyboard(shift_id: int):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Удалить",
            callback_data=f"admin_shift_delete_confirm:{shift_id}",
        )
        builder.button(text="Отмена", callback_data="admin_shift_refresh")
        builder.adjust(1)
        return builder.as_markup()

    async def render_shifts(target: Message | CallbackQuery):
        shifts = await shift_admin.list_today_shifts()
        if shifts:
            text = "📅 Смены на сегодня:\n" + "\n".join(format_shift(s) for s in shifts)
        else:
            text = "📭 Смен на сегодня нет."

        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=build_shift_list_keyboard(shifts))
        else:
            await target.answer(text, reply_markup=build_shift_list_keyboard(shifts))

    @router.callback_query(F.data == "admin_shifts")
    async def admin_shifts_menu(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        await render_shifts(callback)
        await callback.answer()

    @router.callback_query(F.data == "admin_shift_refresh")
    async def shift_refresh(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        await render_shifts(callback)
        await callback.answer()

    @router.callback_query(F.data == "admin_shift_create")
    async def shift_create(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        await callback.message.edit_text(
            "🛠️ Выберите тип смены:", reply_markup=build_create_type_keyboard()
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_shift_create_type:"))
    async def shift_create_type(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, shift_type = callback.data.split(":", 1)
        workers = await shift_admin.list_workers()
        if not workers:
            await callback.message.edit_text(
                "⚠️ Список сотрудников пуст.", reply_markup=build_create_type_keyboard()
            )
            await callback.answer()
            return
        workers.sort(key=lambda w: w.full_name)
        await callback.message.edit_text(
            "👩‍⚕️ Выберите доктора:",
            reply_markup=build_doctors_keyboard(workers, shift_type, page=0),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_shift_doctors:"))
    async def shift_doctors_page(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, shift_type, page_str = callback.data.split(":")
        workers = await shift_admin.list_workers()
        workers.sort(key=lambda w: w.full_name)
        await callback.message.edit_reply_markup(
            reply_markup=build_doctors_keyboard(
                workers, shift_type, page=int(page_str)
            )
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_shift_create_doctor:"))
    async def shift_create_doctor(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, shift_type, doctor_id = callback.data.split(":")
        doctor = await shift_admin.get_worker(int(doctor_id))
        if not doctor:
            await callback.answer("Доктор не найден", show_alert=True)
            return
        success = await shift_admin.create_shift_today(doctor.full_name, shift_type)
        if success:
            await callback.answer("✅ Смена создана")
        else:
            await callback.answer("⚠️ Смена уже существует", show_alert=True)
        await render_shifts(callback)

    @router.callback_query(F.data.startswith("admin_shift_delete:"))
    async def shift_delete(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, shift_id = callback.data.split(":")
        shift = await shift_admin.get_shift(int(shift_id))
        if not shift:
            await callback.answer("Смена не найдена", show_alert=True)
            return
        await callback.message.edit_text(
            f"🗑️ Удалить смену?\n{format_shift(shift)}",
            reply_markup=build_delete_confirm_keyboard(int(shift_id)),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_shift_delete_confirm:"))
    async def shift_delete_confirm(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, shift_id = callback.data.split(":")
        success = await shift_admin.delete_shift_today(int(shift_id))
        if success:
            await callback.answer("🗑️ Смена удалена")
        else:
            await callback.answer("⛔ Удаление недоступно", show_alert=True)
        await render_shifts(callback)

    @router.callback_query(F.data == "admin_shift_delete_menu")
    async def shift_delete_menu(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        shifts = await shift_admin.list_today_shifts()
        if not shifts:
            await callback.answer("📭 Смен на сегодня нет", show_alert=True)
            await render_shifts(callback)
            return
        await callback.message.edit_text(
            "🗑️ Выберите смену для удаления:",
            reply_markup=build_shift_delete_keyboard(shifts),
        )
        await callback.answer()

    return router
    def build_shift_delete_keyboard(shifts: list[Shift]):
        builder = InlineKeyboardBuilder()
        for shift in shifts:
            label = f"Удалить #{shift.id} {shift.doctor_name}"[:64]
            builder.button(text=label, callback_data=f"admin_shift_delete:{shift.id}")
        builder.button(text="Назад", callback_data="admin_shift_refresh")
        builder.adjust(1)
        return builder.as_markup()
