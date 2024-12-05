from apscheduler.schedulers.background import BackgroundScheduler

from reg import start, handle_name_selection, handle_confirmation, handle_photo
from survey import *


# Настройка планировщика
scheduler = BackgroundScheduler()

# Функция для запуска планировщика
scheduler.add_job(run_survey_dispatch, 'cron', hour=16, minute=6)
scheduler.start()

# Запуск бота
bot.polling(none_stop=True)