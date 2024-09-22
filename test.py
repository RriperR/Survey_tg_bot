try:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
            INSERT INTO survey_responses (respondent, subject, questionnaire, timestamp, question1, answer1, question2, answer2, question3, answer3, question4, answer4, question5, answer5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
    row_data[0], row_data[1], row_data[2], datetime.datetime.now(), row_data[4], row_data[5], row_data[6], row_data[7],
    row_data[8], row_data[9], row_data[10], row_data[11], row_data[12], row_data[13]))

    conn.commit()
    cursor.close()
    conn.close()
except Exception as ex:
    print(f"Не удалось сохранить в базу данных: {ex}")