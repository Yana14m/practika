# получение заданий

from bs4 import BeautifulSoup


def get_tasks(session):
    response = session.get("https://pro.guap.ru/inside/student/tasks/?perPage=100")

    html = response.text

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")

    if table is None:
        raise Exception("Таблица не найдена!")

    rows = table.find_all("tr")

    tasks = []

    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        if len(cells) < 10:
            continue

        task_info = {
            "subject": cells[1].get_text(strip=True),
            "number": cells[2].get_text(strip=True),
            "task": cells[3].get_text(strip=True),
            "status": cells[4].get_text(strip=True),
            "score": cells[5].get_text(strip=True),
            "type": cells[6].get_text(strip=True),
            "deadline": cells[7].get_text(strip=True),
            "updated": cells[8].get_text(strip=True),
            "teacher": cells[9].get_text(strip=True),
        }
        tasks.append(task_info)

    return tasks
