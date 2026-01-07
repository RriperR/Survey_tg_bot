from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.use_cases.instrument_admin import InstrumentAdminService
from app.domain.entities import Cabinet, Instrument, InstrumentMove
from app.logger import setup_logger


logger = setup_logger("instrument_admin", "instrument_admin.log")


class InstrumentAdminState(StatesGroup):
    waiting_cabinet_name = State()
    waiting_cabinet_rename = State()
    waiting_instrument_name = State()
    waiting_instrument_rename = State()


def create_instrument_admin_router(
    admin_service: InstrumentAdminService,
    admin_chat_ids: set[str],
) -> Router:
    router = Router()

    def is_admin(user_id: int) -> bool:
        return str(user_id) in admin_chat_ids

    def build_admin_menu():
        builder = InlineKeyboardBuilder()
        builder.button(text="Кабинеты", callback_data="admin_cabinets")
        builder.button(text="Инструменты", callback_data="admin_instruments")
        builder.button(text="Перемещения", callback_data="admin_moves")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_list_keyboard(cabinets: list[Cabinet], view: str):
        builder = InlineKeyboardBuilder()
        for cabinet in cabinets:
            label = cabinet.name
            if not cabinet.is_active:
                label = f"{label} (архив)"
            builder.button(text=label[:64], callback_data=f"cabinet_manage:{cabinet.id}")

        toggle_view = "archived" if view == "active" else "active"
        toggle_label = "Показать архив" if view == "active" else "Показать активные"
        builder.button(text=toggle_label, callback_data=f"cabinet_list:{toggle_view}")
        builder.button(text="Добавить кабинет", callback_data="cabinet_add")
        builder.button(text="Назад", callback_data="admin_back")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_manage_keyboard(cabinet: Cabinet):
        builder = InlineKeyboardBuilder()
        builder.button(text="Переименовать", callback_data=f"cabinet_rename:{cabinet.id}")
        if cabinet.is_active:
            builder.button(text="Архивировать", callback_data=f"cabinet_archive:{cabinet.id}")
        else:
            builder.button(text="Вернуть из архива", callback_data=f"cabinet_restore:{cabinet.id}")
        builder.button(text="Удалить", callback_data=f"cabinet_delete:{cabinet.id}")
        builder.button(text="К списку", callback_data="cabinet_list:active")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_delete_keyboard(cabinet_id: int):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Подтвердить удаление", callback_data=f"cabinet_delete_confirm:{cabinet_id}"
        )
        builder.button(text="Отмена", callback_data=f"cabinet_manage:{cabinet_id}")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_select_keyboard(cabinets: list[Cabinet], view: str):
        builder = InlineKeyboardBuilder()
        for cabinet in cabinets:
            label = cabinet.name
            if not cabinet.is_active:
                label = f"{label} (архив)"
            builder.button(
                text=label[:64], callback_data=f"instrument_list:{cabinet.id}:{view}"
            )
        toggle_view = "archived" if view == "active" else "active"
        toggle_label = "Показать архивные" if view == "active" else "Показать активные"
        builder.button(text=toggle_label, callback_data=f"instrument_cabinets:{toggle_view}")
        builder.button(text="Назад", callback_data="admin_back")
        builder.adjust(1)
        return builder.as_markup()

    def build_instrument_list_keyboard(
        instruments: list[Instrument],
        cabinet_id: int,
        view: str,
    ):
        builder = InlineKeyboardBuilder()
        for instrument in instruments:
            label = instrument.name
            if not instrument.is_active:
                label = f"{label} (архив)"
            builder.button(
                text=label[:64],
                callback_data=f"instrument_manage:{instrument.id}:{cabinet_id}:{view}",
            )
        toggle_view = "archived" if view == "active" else "active"
        toggle_label = "Показать архивные" if view == "active" else "Показать активные"
        builder.button(
            text=toggle_label, callback_data=f"instrument_list:{cabinet_id}:{toggle_view}"
        )
        builder.button(text="Добавить инструмент", callback_data=f"instrument_add:{cabinet_id}")
        builder.button(text="К кабинетам", callback_data="admin_instruments")
        builder.adjust(1)
        return builder.as_markup()

    def build_instrument_manage_keyboard(
        instrument: Instrument, cabinet_id: int, view: str
    ):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Переименовать",
            callback_data=f"instrument_rename:{instrument.id}:{cabinet_id}:{view}",
        )
        if instrument.is_active:
            builder.button(
                text="Архивировать",
                callback_data=f"instrument_archive:{instrument.id}:{cabinet_id}:{view}",
            )
        else:
            builder.button(
                text="Вернуть из архива",
                callback_data=f"instrument_restore:{instrument.id}:{cabinet_id}:{view}",
            )
        builder.button(
            text="Удалить",
            callback_data=f"instrument_delete:{instrument.id}:{cabinet_id}:{view}",
        )
        builder.button(
            text="К списку",
            callback_data=f"instrument_list:{cabinet_id}:{view}",
        )
        builder.adjust(1)
        return builder.as_markup()

    def build_instrument_delete_keyboard(instrument_id: int, cabinet_id: int, view: str):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Подтвердить удаление",
            callback_data=f"instrument_delete_confirm:{instrument_id}:{cabinet_id}:{view}",
        )
        builder.button(
            text="Отмена",
            callback_data=f"instrument_manage:{instrument_id}:{cabinet_id}:{view}",
        )
        builder.adjust(1)
        return builder.as_markup()

    def build_moves_keyboard(moves: list[InstrumentMove]):
        builder = InlineKeyboardBuilder()
        for move in moves:
            builder.row(
                InlineKeyboardButton(
                    text=f"Фото до #{move.id}",
                    callback_data=f"move_photo:before:{move.id}",
                ),
                InlineKeyboardButton(
                    text=f"Фото после #{move.id}",
                    callback_data=f"move_photo:after:{move.id}",
                ),
            )
        builder.row(InlineKeyboardButton(text="Обновить", callback_data="admin_moves"))
        builder.row(InlineKeyboardButton(text="Назад", callback_data="admin_back"))
        return builder.as_markup()

    async def require_admin(callback: CallbackQuery | Message) -> bool:
        user_id = callback.from_user.id
        if not is_admin(user_id):
            if isinstance(callback, CallbackQuery):
                await callback.answer("Нет доступа", show_alert=True)
            else:
                await callback.answer("Нет доступа")
            return False
        return True

    async def render_cabinet_list(callback: CallbackQuery, view: str):
        cabinets = await admin_service.list_cabinets(include_archived=True)
        if view == "archived":
            cabinets = [c for c in cabinets if not c.is_active]
        else:
            cabinets = [c for c in cabinets if c.is_active]
        text = "Кабинеты (архив)" if view == "archived" else "Кабинеты"
        await callback.message.edit_text(
            text,
            reply_markup=build_cabinet_list_keyboard(cabinets, view=view),
        )

    async def render_instrument_cabinets(callback: CallbackQuery, view: str):
        cabinets = await admin_service.list_cabinets(include_archived=True)
        if view == "archived":
            cabinets = [c for c in cabinets if not c.is_active]
        else:
            cabinets = [c for c in cabinets if c.is_active]
        await callback.message.edit_text(
            "Выберите кабинет:",
            reply_markup=build_cabinet_select_keyboard(cabinets, view=view),
        )

    async def render_instrument_list(callback: CallbackQuery, cabinet_id: int, view: str):
        cabinet = await admin_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("Кабинет не найден", show_alert=True)
            return
        instruments = await admin_service.list_instruments(
            cabinet_id, include_archived=True
        )
        if view == "archived":
            instruments = [item for item in instruments if not item.is_active]
        else:
            instruments = [item for item in instruments if item.is_active]
        header = f"Инструменты в кабинете: {cabinet.name}"
        if view == "archived":
            header += " (архив)"
        await callback.message.edit_text(
            header,
            reply_markup=build_instrument_list_keyboard(
                instruments, cabinet_id=cabinet_id, view=view
            ),
        )

    async def render_moves(callback: CallbackQuery):
        moves = await admin_service.list_recent_moves(limit=10)
        cabinets = await admin_service.list_cabinets(include_archived=True)
        cabinet_map = {c.id: c.name for c in cabinets}
        instruments = []
        for cabinet in cabinets:
            instruments.extend(
                await admin_service.list_instruments(cabinet.id, include_archived=True)
            )
        instrument_map = {i.id: i.name for i in instruments}

        if not moves:
            await callback.message.edit_text(
                "Перемещений пока нет.",
                reply_markup=build_admin_menu(),
            )
            return

        lines = []
        for move in moves:
            inst_name = instrument_map.get(move.instrument_id, f"#{move.instrument_id}")
            from_name = cabinet_map.get(move.from_cabinet_id, f"#{move.from_cabinet_id}")
            to_name = cabinet_map.get(move.to_cabinet_id, f"#{move.to_cabinet_id}")
            lines.append(f"{move.id}) {move.moved_at} — {inst_name}: {from_name} -> {to_name}")

        await callback.message.edit_text(
            "Последние перемещения:\n" + "\n".join(lines),
            reply_markup=build_moves_keyboard(moves),
        )

    @router.message(Command("admin"))
    async def admin_menu(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        await state.clear()
        await message.answer("Админка инструментов:", reply_markup=build_admin_menu())

    @router.callback_query(F.data == "admin_back")
    async def admin_back(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await callback.message.edit_text(
            "Админка инструментов:", reply_markup=build_admin_menu()
        )
        await callback.answer()

    @router.callback_query(F.data == "admin_cabinets")
    async def admin_cabinets(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await render_cabinet_list(callback, view="active")
        await callback.answer()

    @router.callback_query(F.data.startswith("cabinet_list:"))
    async def cabinet_list(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, view = callback.data.split(":", 1)
        await render_cabinet_list(callback, view=view)
        await callback.answer()

    @router.callback_query(F.data == "cabinet_add")
    async def cabinet_add(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await state.set_state(InstrumentAdminState.waiting_cabinet_name)
        await callback.message.edit_text("Введите название нового кабинета:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_cabinet_name))
    async def cabinet_add_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("Название не может быть пустым. Попробуйте ещё раз.")
            return
        await admin_service.add_cabinet(name)
        await state.clear()
        await message.answer("Кабинет добавлен.")
        await message.answer("Кабинеты:", reply_markup=build_admin_menu())

    @router.callback_query(F.data.startswith("cabinet_manage:"))
    async def cabinet_manage(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        cabinet = await admin_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("Кабинет не найден", show_alert=True)
            return
        status = "активен" if cabinet.is_active else "архив"
        await callback.message.edit_text(
            f"Кабинет: {cabinet.name}\nСтатус: {status}",
            reply_markup=build_cabinet_manage_keyboard(cabinet),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("cabinet_rename:"))
    async def cabinet_rename(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await state.set_state(InstrumentAdminState.waiting_cabinet_rename)
        await state.update_data(cabinet_id=cabinet_id)
        await callback.message.edit_text("Введите новое название кабинета:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_cabinet_rename))
    async def cabinet_rename_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("Название не может быть пустым. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        cabinet_id = data.get("cabinet_id")
        if not cabinet_id:
            await state.clear()
            await message.answer("Сессия сброшена. Откройте /admin заново.")
            return
        await admin_service.rename_cabinet(cabinet_id, name)
        await state.clear()
        await message.answer("Название обновлено.")

    @router.callback_query(F.data.startswith("cabinet_archive:"))
    async def cabinet_archive(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await admin_service.set_cabinet_active(cabinet_id, False)
        await callback.answer("Кабинет архивирован")
        await cabinet_manage(callback)

    @router.callback_query(F.data.startswith("cabinet_restore:"))
    async def cabinet_restore(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await admin_service.set_cabinet_active(cabinet_id, True)
        await callback.answer("Кабинет восстановлен")
        await cabinet_manage(callback)

    @router.callback_query(F.data.startswith("cabinet_delete:"))
    async def cabinet_delete(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        cabinet = await admin_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("Кабинет не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"Удалить кабинет «{cabinet.name}»?",
            reply_markup=build_cabinet_delete_keyboard(cabinet_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("cabinet_delete_confirm:"))
    async def cabinet_delete_confirm(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        success = await admin_service.delete_cabinet(cabinet_id)
        if success:
            await callback.answer("Кабинет удалён")
            await render_cabinet_list(callback, view="active")
        else:
            await callback.answer(
                "Нельзя удалить кабинет с инструментами", show_alert=True
            )

    @router.callback_query(F.data == "admin_instruments")
    async def admin_instruments(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await render_instrument_cabinets(callback, view="active")
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_cabinets:"))
    async def instrument_cabinets(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, view = callback.data.split(":", 1)
        await render_instrument_cabinets(callback, view=view)
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_list:"))
    async def instrument_list(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, cabinet_id, view = callback.data.split(":")
        await render_instrument_list(callback, cabinet_id=int(cabinet_id), view=view)
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_manage:"))
    async def instrument_manage(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        instrument = await admin_service.get_instrument(int(instrument_id))
        if not instrument:
            await callback.answer("Инструмент не найден", show_alert=True)
            return
        status = "активен" if instrument.is_active else "архив"
        await callback.message.edit_text(
            f"Инструмент: {instrument.name}\nСтатус: {status}",
            reply_markup=build_instrument_manage_keyboard(
                instrument, cabinet_id=int(cabinet_id), view=view
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_add:"))
    async def instrument_add(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await state.set_state(InstrumentAdminState.waiting_instrument_name)
        await state.update_data(cabinet_id=cabinet_id)
        await callback.message.edit_text("Введите название нового инструмента:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_instrument_name))
    async def instrument_add_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("Название не может быть пустым. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        cabinet_id = data.get("cabinet_id")
        if not cabinet_id:
            await state.clear()
            await message.answer("Сессия сброшена. Откройте /admin заново.")
            return
        await admin_service.add_instrument(cabinet_id, name)
        await state.clear()
        instruments = await admin_service.list_instruments(
            cabinet_id, include_archived=True
        )
        instruments = [item for item in instruments if item.is_active]
        await message.answer("Инструмент добавлен.")
        await message.answer(
            "Инструменты:",
            reply_markup=build_instrument_list_keyboard(
                instruments, cabinet_id=cabinet_id, view="active"
            ),
        )

    @router.callback_query(F.data.startswith("instrument_rename:"))
    async def instrument_rename(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await state.set_state(InstrumentAdminState.waiting_instrument_rename)
        await state.update_data(
            instrument_id=int(instrument_id),
            cabinet_id=int(cabinet_id),
            view=view,
        )
        await callback.message.edit_text("Введите новое название инструмента:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_instrument_rename))
    async def instrument_rename_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("Название не может быть пустым. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        instrument_id = data.get("instrument_id")
        cabinet_id = data.get("cabinet_id")
        view = data.get("view", "active")
        if not instrument_id or not cabinet_id:
            await state.clear()
            await message.answer("Сессия сброшена. Откройте /admin заново.")
            return
        await admin_service.rename_instrument(instrument_id, name)
        await state.clear()
        await message.answer("Название обновлено.")
        instruments = await admin_service.list_instruments(
            cabinet_id, include_archived=True
        )
        if view == "archived":
            instruments = [item for item in instruments if not item.is_active]
        else:
            instruments = [item for item in instruments if item.is_active]
        await message.answer(
            "Инструменты:",
            reply_markup=build_instrument_list_keyboard(
                instruments, cabinet_id=cabinet_id, view=view
            ),
        )

    @router.callback_query(F.data.startswith("instrument_archive:"))
    async def instrument_archive(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await admin_service.set_instrument_active(int(instrument_id), False)
        await callback.answer("Инструмент архивирован")
        await render_instrument_list(callback, int(cabinet_id), view=view)

    @router.callback_query(F.data.startswith("instrument_restore:"))
    async def instrument_restore(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await admin_service.set_instrument_active(int(instrument_id), True)
        await callback.answer("Инструмент восстановлен")
        await render_instrument_list(callback, int(cabinet_id), view=view)

    @router.callback_query(F.data.startswith("instrument_delete:"))
    async def instrument_delete(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        instrument = await admin_service.get_instrument(int(instrument_id))
        if not instrument:
            await callback.answer("Инструмент не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"Удалить инструмент «{instrument.name}»?",
            reply_markup=build_instrument_delete_keyboard(
                int(instrument_id), int(cabinet_id), view
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_delete_confirm:"))
    async def instrument_delete_confirm(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await admin_service.delete_instrument(int(instrument_id))
        await callback.answer("Инструмент удалён")
        await render_instrument_list(callback, int(cabinet_id), view=view)

    @router.callback_query(F.data == "admin_moves")
    async def admin_moves(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await render_moves(callback)
        await callback.answer()

    @router.callback_query(F.data.startswith("move_photo:"))
    async def move_photo(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, kind, move_id = callback.data.split(":")
        move = await admin_service.get_move(int(move_id))
        if not move:
            await callback.answer("Перемещение не найдено", show_alert=True)
            return
        photo_id = move.before_photo_id if kind == "before" else move.after_photo_id
        if not photo_id:
            await callback.answer("Фото отсутствует", show_alert=True)
            return
        caption = "Фото до" if kind == "before" else "Фото после"
        await callback.message.answer_photo(photo=photo_id, caption=caption)
        await callback.answer()

    return router
