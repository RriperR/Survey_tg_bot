import datetime

import psycopg2


class DatabaseManager:
    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password

    def __enter__(self):
        self.conn = psycopg2.connect(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            client_encoding = 'UTF8'
        )
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()  # Откат транзакции при ошибке
        else:
            self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def insert_survey_response(self, row_data):
        query = """
            INSERT INTO survey_responses (subject, object, questionnaire, timestamp, question1, answer1, question2, answer2, question3, answer3, question4, answer4, question5, answer5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = (
            row_data[0], row_data[1], row_data[2], datetime.datetime.now(),
            row_data[4], row_data[5], row_data[6], row_data[7],
            row_data[8], row_data[9], row_data[10], row_data[11],
            row_data[12], row_data[13]
        )
        self.cursor.execute(query, data)
        self.conn.commit()

    def execute(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def fetch_all(self, query):
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            self.conn.rollback()
            raise e

    def fetch_one(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()  # Вернёт кортеж (row) или None
        except Exception as e:
            self.conn.rollback()
            raise e
