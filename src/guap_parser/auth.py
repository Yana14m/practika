import requests
from bs4 import BeautifulSoup


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.get("https://pro.guap.ru/oauth/login")

    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form")
    action = form["action"]

    payload = {
        "username": username,
        "password": password,
        "credentialId": "",
    }
    response = session.post(action, data=payload, allow_redirects=True)

    if "/inside/profile" not in response.url:
        raise Exception("Ошибка авторизации!")

    return session
