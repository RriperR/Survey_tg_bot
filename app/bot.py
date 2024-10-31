import schedule
import threading

from reg import start, handle_name_selection, handle_confirmation, handle_photo
from survey import *


# Запланировать выполнение
schedule.every().day.at("18:23").do(run_survey_dispatch)

# Функция для запуска планировщика
def scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запускаем планировщик в отдельном потоке
scheduler_thread = threading.Thread(target=scheduler)
scheduler_thread.start()

# Запуск бота
bot.polling(none_stop=True)