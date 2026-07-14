# настройки проекта

from dotenv import load_dotenv
import os

load_dotenv()

LOGIN=os.getenv("GUAP_LOGIN")
PASSWORD=os.getenv("GUAP_PASSWORD")

BASE_URL="https://pro.guap.ru/"
TASKS_URL="https://pro.guap.ru/inside/student/tasks/"