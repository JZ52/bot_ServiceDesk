import os
import psycopg2
from psycopg2 import OperationalError
from datetime import datetime, timedelta
from dotenv import load_dotenv


load_dotenv('key.env')

SQL_ADRES = os.getenv("SQL_ADRES")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_PORT = os.getenv("SQL_PORT")

def create_connection():
    try:
        connection = psycopg2.connect(
            host=SQL_ADRES,
            user=SQL_USER,
            password=SQL_PASSWORD,
            database=SQL_DATABASE,
            port=SQL_PORT,
            client_encoding='UTF8'
        )
        cursor = connection.cursor()
        print("Успешное подключение к базе данных")
        return connection
    except OperationalError as e:
        print(f"Ошибка подключения: {e}")
        return None

def get_daily_summary():
    query ="""
    SELECT user_name, COUNT(*) as message_count
    FROM slack_messages
    WHERE date_normal = %s
    GROUP BY user_name
    ORDER BY message_count DESC
    """

    today = datetime.now().date()
    connection = create_connection()
    if connection is None:
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(query,(today,))
            result = cursor.fetchall()
            return result
    except Exception as e:
        print(f"Error query: { e }")
        return []
    finally:
        connection.close()


