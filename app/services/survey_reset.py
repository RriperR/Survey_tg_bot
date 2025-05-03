from aiogram import Bot
from database import requests as rq
from database.models import Pair
from logger import setup_logger

logger = setup_logger("reset", "reset.log")


async def reset_surveys_and_notify_users(bot: Bot) -> None:
    """
    Сброс всех опросов со статусом 'in_progress' и уведомление пользователей
    о технических работах.
    """
    logger.info("⚙️ Сброс опросов: начало")

    pairs: list[Pair] = await rq.get_in_progress_pairs()

    if not pairs:
        logger.info("✅ Нет незавершённых опросов для сброса.")
        return

    subjects = {pair.subject for pair in pairs}
    notified_count = 0
    skipped_count = 0

    for subject in subjects:
        worker = await rq.get_worker_by_fullname(subject)
        if worker and worker.chat_id:
            try:
                await bot.send_message(
                    chat_id=worker.chat_id,
                    text=(
                        "⚠️ *Опрос был сброшен в связи с техническими работами.*\n\n"
                        "Пожалуйста, не нажимайте на кнопки из предыдущего сообщения, "
                        "чтобы избежать ошибок. Мы скоро пришлём вам новый опрос. 🙏"
                    ),
                    parse_mode="Markdown"
                )
                logger.info(f"🔔 Уведомление отправлено: {worker.full_name} ({worker.chat_id})")
                notified_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке сообщения {worker.full_name}: {e}")
        else:
            logger.warning(f"⚠️ Не удалось отправить сообщение: сотрудник '{subject}' не найден или нет chat_id")
            skipped_count += 1

    # Сброс всех in_progress → ready
    await rq.reset_incomplete_surveys()

    logger.info(
        f"✅ Сброшено {len(pairs)} опросов. Уведомлено: {notified_count}, пропущено: {skipped_count}"
    )
