import os
import pandas as pd
import logging

from datetime import datetime, timedelta
from dotenv import load_dotenv

from models import DatabaseManager
from init import bot, DB_HOST, DB_NAME, DB_USER, DB_PASSWORD


load_dotenv()
REPORT_CHAT_ID = int(os.getenv("REPORT_CHAT_ID"))

# Настройка логирования
logger = logging.getLogger("report")  # Отдельный логгер "report"
logger.setLevel(logging.INFO)

handler = logging.FileHandler("/code/logs/report.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


def send_monthly_report():
    try:
        start_date = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).date()
        end_date = datetime.now().replace(day=1).date()

        query = f"""
        SELECT
            a.subject,
            a.object,
            a.questionnaire,
            a.survey_date,
            a.completed_at,
            MAX(CASE WHEN q.rn = 1 THEN q.question_text END) AS question1,
            MAX(CASE WHEN q.rn = 1 THEN q.user_response END) AS answer1,
            MAX(CASE WHEN q.rn = 2 THEN q.question_text END) AS question2,
            MAX(CASE WHEN q.rn = 2 THEN q.user_response END) AS answer2,
            MAX(CASE WHEN q.rn = 3 THEN q.question_text END) AS question3,
            MAX(CASE WHEN q.rn = 3 THEN q.user_response END) AS answer3,
            MAX(CASE WHEN q.rn = 4 THEN q.question_text END) AS question4,
            MAX(CASE WHEN q.rn = 4 THEN q.user_response END) AS answer4,
            MAX(CASE WHEN q.rn = 5 THEN q.question_text END) AS question5,
            MAX(CASE WHEN q.rn = 5 THEN q.user_response END) AS answer5
        FROM survey_assignments a
        LEFT JOIN (
            SELECT 
                q.*,
                ROW_NUMBER() OVER (PARTITION BY q.survey_id ORDER BY q.id) AS rn
            FROM survey_questions q
        ) q ON a.id = q.survey_id
        WHERE a.survey_date >= %s AND a.survey_date < %s
        GROUP BY a.id
        ORDER BY a.id;
        """

        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            db.cursor.execute(query, (start_date, end_date))
            rows = db.cursor.fetchall()
            columns = [desc[0] for desc in db.cursor.description]

        df = pd.DataFrame(rows, columns=columns)
        filename = f"monthly_report_{start_date}.csv"
        df.to_csv(filename, index=False)

        with open(filename, "rb") as f:
            bot.send_document(REPORT_CHAT_ID, f, caption=f"Отчёт за {start_date.strftime('%B %Y')}")

    except Exception as e:
        logger.error(f"Ошибка при отправке отчёта: {e}")
