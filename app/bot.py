import os

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from reg import start, handle_name_selection, handle_confirmation, handle_photo
from survey import *
from report import send_monthly_report

# Сразу при старте один раз загрузим данные.
update_local_cache()

# Настройка планировщика
scheduler = BackgroundScheduler()

# Функции для запуска планировщика
scheduler.add_job(update_local_cache, 'cron', hour=19, minute=50)

scheduler.add_job(run_survey_dispatch, 'cron', hour=20, minute=30)

scheduler.add_job(send_monthly_report, 'cron', day=4, hour=20, minute=52)

scheduler.start()

# Запуск бота
bot.polling(none_stop=True)
