# авторизация в ГУАП

import requests
from bs4 import BeautifulSoup
from config import LOGIN, PASSWORD

def login():
    session=requests.Session()

    response=session.get("https://pro.guap.ru/oauth/login")

    soup=BeautifulSoup(response.text, "html.parser")

    form=soup.find("form")

    action=form["action"]

    payload={
        "username": LOGIN,
        "password": PASSWORD,
        "credentialId": ""
    }
    response=session.post(
        action,
        data=payload,
        allow_redirects=True
    )

    if "/inside/profile" not in response.url:
        raise Exception("Ошибка авторизации!")
    print("Авторизация успешная!")

    return session