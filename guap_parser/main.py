# запуск программы

from config import LOGIN, PASSWORD
from auth import login
from parser import get_tasks

def print_tasks(tasks):
    if not tasks:
        print("Все задания уже приняты!")
        return
    for task in tasks:
        print(f"Дисциплина: {task['subject']}")
        print(f"Задание: {task['task']}")
        print(f"Дедлайн: {task['deadline']}")
        print(f"Преподаватель: {task['teacher']}")
        print(f"Статус: {task['status']}")

session=login()
tasks=get_tasks(session)
unfinished_tasks=[
    task for task in tasks
    if task["status"]!="принят"
]
print_tasks(unfinished_tasks)

#print(LOGIN)
#print(PASSWORD)