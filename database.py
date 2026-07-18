"""
Модуль базы данных для MAX-бота.

Этот модуль отвечает за хранение всех данных проекта:
- пользователей бота
- дисциплин (предметов)
- заданий с дедлайнами

Все функции модуля используют SQLite — встроенную в Python базу данных.
Ничего дополнительно устанавливать НЕ НУЖНО.

Автор: Участник №3 (Базы данных)
Группа: 1442
"""


# ПОДКЛЮЧАЕМ НЕОБХОДИМЫЕ МОДУЛИ

# Модуль для работы с SQLite (встроен в Python, ничего не устанавливаем)
import sqlite3

# Модуль для записи ошибок и событий (встроен в Python)
import logging

# Модуль для работы с датой и временем (встроен в Python)
from datetime import datetime, timedelta

# Модуль для подсказок типов (помогает в коде, но не обязателен)
from typing import Optional, List, Dict, Any


# НАСТРОЙКА ЛОГИРОВАНИЯ

# Настраиваем логирование, чтобы все важные события записывались
# level=logging.INFO означает, что мы будем видеть информационные сообщения
logging.basicConfig(level=logging.INFO)

# Создаём объект для записи логов с именем текущего файла
logger = logging.getLogger(__name__)


# ИМЯ ФАЙЛА БАЗЫ ДАННЫХ

# Здесь хранится имя файла, в который будет сохраняться база данных
# При первом запуске этот файл создастся автоматически в папке с проектом
DB_NAME = 'max_bot.db'


# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ

def get_connection() -> sqlite3.Connection:
    """
    Устанавливает соединение с базой данных.
    
    Эта функция нужна, чтобы каждый раз не писать код подключения заново.
    row_factory настроен так, чтобы результаты запросов возвращались в виде словарей.
    Это значит, что к данным можно обращаться по имени колонки: row['name'].
    
    Returns:
        sqlite3.Connection: объект соединения с базой данных
    """
    # Подключаемся к файлу базы данных
    # Если файла нет, он создастся автоматически
    conn = sqlite3.connect(DB_NAME)
    
    # Настраиваем, чтобы результат запроса можно было получать по имени колонки
    # Например: row['name'] вместо row[0]
    conn.row_factory = sqlite3.Row
    
    # Возвращаем соединение
    return conn


# ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ТАБЛИЦ

def init_db() -> None:
    """
    Создаёт все необходимые таблицы, если они ещё не существуют.
    
    Эту функцию нужно вызвать ОДИН РАЗ при первом запуске бота.
    Если таблицы уже есть, она просто ничего не сделает.
    
    В проекте три таблицы:
    1. users — пользователи бота
    2. disciplines — дисциплины (предметы)
    3. assignments — задания с дедлайнами
    """
    
    # Устанавливаем соединение с базой данных
    conn = get_connection()
    
    # Создаём курсор — объект, через который мы отправляем запросы в базу
    cursor = conn.cursor()
    
    
    # СОЗДАЁМ ТАБЛИЦУ 1: ПОЛЬЗОВАТЕЛИ (users)
    
    # Эта таблица хранит информацию о каждом пользователе бота
    # Когда пользователь первый раз запускает бота, мы добавляем его сюда
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            -- id: уникальный номер записи. Заполняется автоматически (1, 2, 3...)
            
            user_id TEXT UNIQUE NOT NULL,
            -- user_id: уникальный идентификатор пользователя в MAX.
            -- Его передаёт сам MAX при старте бота. 
            -- UNIQUE означает, что два одинаковых user_id быть не может.
            -- NOT NULL означает, что поле обязательно должно быть заполнено.
            
            login TEXT,
            -- login: логин от личного кабинета вуза.
            -- Пользователь вводит его при настройке аккаунта.
            
            password TEXT,
            -- password: пароль от личного кабинета вуза.
            -- Пока хранится открыто, в будущем нужно шифровать.
            
            is_active INTEGER DEFAULT 1,
            -- is_active: активен ли пользователь.
            -- 1 — активен, 0 — удалён (мягкое удаление).
            -- DEFAULT 1 означает, что по умолчанию ставится 1.
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            -- created_at: дата и время регистрации пользователя.
            -- DEFAULT CURRENT_TIMESTAMP — ставится текущее время автоматически.
        )
    ''')
    
    
    # СОЗДАЁМ ТАБЛИЦУ 2: ДИСЦИПЛИНЫ (disciplines)
    
    # Эта таблица хранит список предметов для каждого пользователя
    # Один пользователь может иметь много дисциплин
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disciplines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            -- id: уникальный номер записи
            
            user_id INTEGER NOT NULL,
            -- user_id: ID пользователя из таблицы users.
            -- Это внешний ключ — он ссылается на таблицу users.
            -- NOT NULL означает, что каждая дисциплина обязательно принадлежит кому-то.
            
            name TEXT NOT NULL,
            -- name: название дисциплины. Например, "Математика" или "Программирование".
            -- NOT NULL — название обязательно должно быть.
            
            teacher TEXT,
            -- teacher: имя преподавателя. Необязательное поле.
            
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            -- FOREIGN KEY: это поле является внешним ключом.
            -- REFERENCES users(id): оно ссылается на поле id в таблице users.
            -- ON DELETE CASCADE: если пользователя удалят, все его дисциплины удалятся автоматически.
        )
    ''')
    
    
    # СОЗДАЁМ ТАБЛИЦУ 3: ЗАДАНИЯ (assignments)
    
    # Эта таблица хранит все учебные задания с дедлайнами
    # Каждое задание относится к какой-то дисциплине
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            -- id: уникальный номер записи
            
            discipline_id INTEGER NOT NULL,
            -- discipline_id: ID дисциплины из таблицы disciplines.
            -- Это внешний ключ — задание принадлежит конкретной дисциплине.
            
            title TEXT NOT NULL,
            -- title: название задания.
            -- Например, "Домашняя работа №1" или "Лабораторная работа №3".
            
            deadline DATETIME NOT NULL,
            -- deadline: дата и время сдачи задания.
            -- Формат: "YYYY-MM-DD HH:MM:SS" (например, "2026-07-20 23:59:00").
            
            status TEXT DEFAULT 'active',
            -- status: статус задания.
            -- 'active' — активное (ещё не сдано)
            -- 'completed' — сдано
            -- 'overdue' — просрочено
            -- DEFAULT 'active' — по умолчанию ставится 'active'.
            
            notified_1day INTEGER DEFAULT 0,
            -- notified_1day: отправляли ли уведомление за 1 день.
            -- 0 — ещё не отправляли, 1 — уже отправили.
            -- Это нужно, чтобы не дублировать уведомления.
            
            source_id TEXT,
            -- source_id: ID задания из личного кабинета вуза.
            -- Используется для синхронизации, чтобы не создавать дубли.
            
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            -- last_updated: дата и время последнего обновления записи.
            -- Ставится автоматически при создании или изменении.
            
            FOREIGN KEY (discipline_id) REFERENCES disciplines(id) ON DELETE CASCADE
            -- Если дисциплину удалят, все её задания удалятся автоматически.
        )
    ''')
    
    
    # СОЗДАЁМ ИНДЕКСЫ ДЛЯ УСКОРЕНИЯ ПОИСКА
    
    # Индексы — это как оглавление в книге. Они ускоряют поиск данных.
    # Без индексов база данных просматривает все записи подряд, что медленно.
    
    # Индекс для быстрого поиска по дате дедлайна
    # Пригодится, когда мы будем искать задания с ближайшими дедлайнами
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_deadline ON assignments(deadline)')
    
    # Индекс для быстрого поиска по статусу
    # Пригодится, когда мы будем искать только активные задания
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status)')
    
    
    # СОХРАНЯЕМ ИЗМЕНЕНИЯ И ЗАКРЫВАЕМ СОЕДИНЕНИЕ
    
    # commit — сохраняет все изменения в файл. Без этого они не запишутся.
    conn.commit()
    
    # close — закрывает соединение с базой. Важно делать, чтобы не было утечек.
    conn.close()
    
    # Пишем в лог, что всё успешно создалось
    logger.info("База данных и таблицы созданы (или уже существуют).")


# ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ

def add_user(user_id: str, login: str = '', password: str = '') -> int:
    """
    Добавляет нового пользователя в базу данных.
    
    Эту функцию будет вызывать модуль бота (участник №1), 
    когда пользователь первый раз запускает бота или настраивает аккаунт.
    
    Параметры:
        user_id (str): уникальный ID пользователя в MAX.
                       Его передаёт сам MAX при старте бота.
        login (str): логин от личного кабинета вуза. Необязательный параметр.
        password (str): пароль от личного кабинета вуза. Необязательный параметр.
    
    Возвращает:
        int: внутренний ID пользователя в базе данных.
             Он нужен для других функций (например, чтобы добавить дисциплину).
             Если произошла ошибка, возвращает -1.
    """
    
    # Устанавливаем соединение с базой данных
    conn = get_connection()
    
    # Создаём курсор для отправки запросов
    cursor = conn.cursor()
    
    # Пытаемся выполнить запрос. Если возникнет ошибка, мы её поймаем.
    try:
        
        # INSERT — добавляем новую запись в таблицу users
        # OR IGNORE — если пользователь с таким user_id уже есть, ничего не делаем
        # (это защита от дублирования)
        # Вместо вопросиков подставляются значения из кортежа (user_id, login, password)
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, login, password) VALUES (?, ?, ?)",
            (user_id, login, password)
        )
        
        # Сохраняем изменения в файле базы данных
        conn.commit()
        
        # Теперь нужно получить ID только что добавленного пользователя
        # SELECT — выбираем запись
        # WHERE user_id = ? — ищем пользователя с нужным user_id
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        
        # fetchone — получаем одну запись (первую из найденных)
        row = cursor.fetchone()
        
        # Если запись найдена, возвращаем её ID
        # Если не найдена, возвращаем -1 (это означает ошибку)
        if row:
            return row['id']  # row['id'] — обращаемся к колонке по имени
        else:
            return -1
    
    except Exception as e:
        # Если произошла ошибка (например, проблема с базой данных)
        # Пишем в лог сообщение об ошибке
        logger.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
        # Возвращаем -1, чтобы вызвавшая функция знала, что что-то пошло не так
        return -1
    
    finally:
        # ВАЖНО: закрываем соединение в любом случае (даже если была ошибка)
        # Это предотвращает утечки памяти и проблемы с доступом к файлу
        conn.close()


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает данные пользователя по его ID в MAX.
    
    Эту функцию будет вызывать бот (участник №1), когда нужно проверить,
    зарегистрирован ли пользователь и есть ли у него логин с паролем.
    
    Параметры:
        user_id (str): уникальный ID пользователя в MAX.
    
    Возвращает:
        dict: словарь с данными пользователя (все поля из таблицы users).
              Если пользователь не найден или произошла ошибка, возвращает None.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # SELECT * — выбираем все поля из таблицы users
        # WHERE — ищем пользователя с нужным user_id
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        
        # Получаем одну запись
        row = cursor.fetchone()
        
        # Если запись есть, преобразуем её в обычный словарь и возвращаем
        # Если нет — возвращаем None
        if row:
            return dict(row)
        else:
            return None
    
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
        return None
    
    finally:
        conn.close()


def update_user_password(user_id: str, new_password: str) -> bool:
    """
    Обновляет пароль пользователя.
    
    Эту функцию будет вызывать бот (участник №1), 
    когда пользователь меняет пароль от личного кабинета.
    
    Параметры:
        user_id (str): уникальный ID пользователя в MAX.
        new_password (str): новый пароль.
    
    Возвращает:
        bool: True — если пароль успешно обновлён.
              False — если произошла ошибка или пользователь не найден.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # UPDATE — обновляем запись
        # SET password = ? — устанавливаем новое значение пароля
        # WHERE user_id = ? — обновляем только для конкретного пользователя
        cursor.execute(
            "UPDATE users SET password = ? WHERE user_id = ?",
            (new_password, user_id)
        )
        
        conn.commit()
        
        # rowcount — сколько записей было изменено
        # Если > 0, значит обновление прошло успешно
        return cursor.rowcount > 0
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении пароля для {user_id}: {e}")
        return False
    
    finally:
        conn.close()


def delete_user(user_id: str) -> bool:
    """
    Мягкое удаление пользователя.
    
    Мы не удаляем запись полностью, а просто помечаем пользователя как неактивного.
    Это называется "мягкое удаление" — данные сохраняются для истории.
    
    Эту функцию будет вызывать бот, если пользователь хочет удалить аккаунт.
    
    Параметры:
        user_id (str): уникальный ID пользователя в MAX.
    
    Возвращает:
        bool: True — если пользователь успешно деактивирован.
              False — если произошла ошибка.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # UPDATE — обновляем is_active на 0 (пользователь неактивен)
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя {user_id}: {e}")
        return False
    
    finally:
        conn.close()


# ФУНКЦИИ ДЛЯ РАБОТЫ С ДИСЦИПЛИНАМИ

def add_discipline(user_id: int, name: str, teacher: str = None) -> int:
    """
    Добавляет дисциплину для пользователя.
    
    Эту функцию будет вызывать модуль синхронизации (участник №2),
    когда он получает список предметов из личного кабинета.
    
    Параметры:
        user_id (int): внутренний ID пользователя из таблицы users.
                       Его возвращает функция add_user.
        name (str): название дисциплины. Например, "Математика".
        teacher (str): преподаватель. Необязательный параметр.
    
    Возвращает:
        int: ID добавленной дисциплины в базе данных.
             Если произошла ошибка, возвращает -1.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # INSERT — добавляем новую дисциплину
        cursor.execute(
            "INSERT INTO disciplines (user_id, name, teacher) VALUES (?, ?, ?)",
            (user_id, name, teacher)
        )
        
        conn.commit()
        
        # lastrowid — возвращает ID последней вставленной записи
        return cursor.lastrowid
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении дисциплины {name}: {e}")
        return -1
    
    finally:
        conn.close()


def get_disciplines(user_id: int) -> List[Dict[str, Any]]:
    """
    Получает все дисциплины пользователя.
    
    Эту функцию может вызывать бот (участник №1), 
    чтобы показать пользователю список его предметов.
    
    Параметры:
        user_id (int): внутренний ID пользователя из таблицы users.
    
    Возвращает:
        list: список словарей с данными дисциплин.
              Каждый словарь содержит поля: id, user_id, name, teacher.
              Если дисциплин нет или произошла ошибка, возвращает пустой список [].
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # SELECT * — выбираем все поля
        # WHERE user_id = ? — ищем дисциплины конкретного пользователя
        cursor.execute("SELECT * FROM disciplines WHERE user_id = ?", (user_id,))
        
        # fetchall — получаем все найденные записи
        rows = cursor.fetchall()
        
        # Преобразуем каждую запись в словарь и возвращаем список
        # Если записей нет, возвращаем пустой список
        return [dict(row) for row in rows]
    
    except Exception as e:
        logger.error(f"Ошибка при получении дисциплин для пользователя {user_id}: {e}")
        return []
    
    finally:
        conn.close()


def get_discipline_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """
    Находит дисциплину по названию для конкретного пользователя.
    
    Эта функция нужна для синхронизации — чтобы не создавать дубли дисциплин.
    
    Параметры:
        user_id (int): внутренний ID пользователя.
        name (str): название дисциплины.
    
    Возвращает:
        dict: словарь с данными дисциплины, если найдена.
        None: если не найдена или произошла ошибка.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Ищем дисциплину с нужным названием у конкретного пользователя
        cursor.execute(
            "SELECT * FROM disciplines WHERE user_id = ? AND name = ?",
            (user_id, name)
        )
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    except Exception as e:
        logger.error(f"Ошибка при поиске дисциплины {name}: {e}")
        return None
    
    finally:
        conn.close()


# ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАДАНИЯМИ

def add_assignment(discipline_id: int, title: str, deadline: str, source_id: str = None) -> int:
    """
    Добавляет новое задание в базу данных.
    
    Эту функцию будет вызывать модуль синхронизации (участник №2),
    когда он получает список заданий из личного кабинета.
    
    Параметры:
        discipline_id (int): ID дисциплины из таблицы disciplines.
        title (str): название задания. Например, "Домашняя работа №1".
        deadline (str): дата и время сдачи в формате "YYYY-MM-DD HH:MM:SS".
        source_id (str): ID задания из личного кабинета. Используется для синхронизации.
    
    Возвращает:
        int: ID добавленного задания в базе данных.
             Если произошла ошибка, возвращает -1.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # INSERT — добавляем новое задание
        cursor.execute(
            """
            INSERT INTO assignments (discipline_id, title, deadline, source_id)
            VALUES (?, ?, ?, ?)
            """,
            (discipline_id, title, deadline, source_id)
        )
        
        conn.commit()
        return cursor.lastrowid
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении задания {title}: {e}")
        return -1
    
    finally:
        conn.close()


def get_assignments(user_id: int) -> List[Dict[str, Any]]:
    """
    Получает все задания пользователя с названиями дисциплин.
    
    Эту функцию будет вызывать бот (участник №1), когда пользователь 
    нажимает кнопку "Мои задания".
    
    Параметры:
        user_id (int): внутренний ID пользователя из таблицы users.
    
    Возвращает:
        list: список словарей с заданиями.
              Каждый словарь содержит: id, title, deadline, status, notified_1day, discipline_name.
              Задания сортируются по дате дедлайна (сначала ближайшие).
              Если заданий нет, возвращает пустой список [].
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # SELECT a.* — выбираем все поля из таблицы assignments
        # d.name as discipline_name — выбираем название дисциплины и называем его discipline_name
        # FROM assignments a JOIN disciplines d — объединяем две таблицы
        # ON a.discipline_id = d.id — условие объединения
        # WHERE d.user_id = ? — ищем задания конкретного пользователя
        # ORDER BY a.deadline ASC — сортируем по дате дедлайна (ASC — по возрастанию)
        cursor.execute('''
            SELECT 
                a.id, 
                a.title, 
                a.deadline, 
                a.status, 
                a.notified_1day,
                d.name as discipline_name
            FROM assignments a
            JOIN disciplines d ON a.discipline_id = d.id
            WHERE d.user_id = ?
            ORDER BY a.deadline ASC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    except Exception as e:
        logger.error(f"Ошибка при получении заданий для пользователя {user_id}: {e}")
        return []
    
    finally:
        conn.close()


def get_assignments_soon(user_id: int, days: int = 3) -> List[Dict[str, Any]]:
    """
    Получает задания с дедлайном в ближайшие N дней.
    
    Эту функцию будет вызывать бот (участник №1), когда пользователь 
    нажимает кнопку "Ближайшие дедлайны".
    
    Параметры:
        user_id (int): внутренний ID пользователя.
        days (int): количество дней для поиска. По умолчанию 3 дня.
    
    Возвращает:
        list: список словарей с заданиями, у которых дедлайн в ближайшие days дней.
              Каждый словарь содержит: id, title, deadline, discipline_name.
              Если таких заданий нет, возвращает пустой список [].
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем текущую дату и время в формате для SQLite
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Получаем дату через days дней
        future = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Ищем задания, у которых дедлайн между now и future
        # И только активные задания (status = 'active')
        cursor.execute('''
            SELECT 
                a.id, 
                a.title, 
                a.deadline, 
                d.name as discipline_name
            FROM assignments a
            JOIN disciplines d ON a.discipline_id = d.id
            WHERE d.user_id = ? 
              AND a.deadline BETWEEN ? AND ?
              AND a.status = 'active'
            ORDER BY a.deadline ASC
        ''', (user_id, now, future))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    except Exception as e:
        logger.error(f"Ошибка при получении ближайших заданий: {e}")
        return []
    
    finally:
        conn.close()


def get_assignment_by_id(assignment_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает задание по его ID.
    
    Эта функция нужна для проверки деталей конкретного задания.
    
    Параметры:
        assignment_id (int): ID задания из таблицы assignments.
    
    Возвращает:
        dict: словарь с данными задания, если найдено.
        None: если не найдено или произошла ошибка.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    except Exception as e:
        logger.error(f"Ошибка при получении задания {assignment_id}: {e}")
        return None
    
    finally:
        conn.close()


def mark_notification_sent(assignment_id: int) -> bool:
    """
    Отмечает, что уведомление за 1 день уже отправлено.
    
    Эту функцию будет вызывать модуль уведомлений (участник №4),
    после того как он отправил пользователю уведомление.
    
    Параметры:
        assignment_id (int): ID задания из таблицы assignments.
    
    Возвращает:
        bool: True — если отметка успешно установлена.
              False — если произошла ошибка.
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # UPDATE — обновляем notified_1day на 1 (уведомление отправлено)
        cursor.execute(
            "UPDATE assignments SET notified_1day = 1 WHERE id = ?",
            (assignment_id,)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    
    except Exception as e:
        logger.error(f"Ошибка при отметке уведомления для задания {assignment_id}: {e}")
        return False
    
    finally:
        conn.close()


def get_users_for_notification(days: int = 1) -> List[Dict[str, Any]]:
    """
    Получает список пользователей и их заданий для отправки уведомлений.
    
    Эту функцию будет вызывать модуль уведомлений (участник №4) по расписанию.
    Она находит все задания, у которых:
    - дедлайн наступает через days дней (по умолчанию через 1 день)
    - уведомление ещё не отправлено (notified_1day = 0)
    - задание активное (status = 'active')
    - пользователь активен (is_active = 1)
    
    Параметры:
        days (int): через сколько дней наступает дедлайн. По умолчанию 1 день.
    
    Возвращает:
        list: список словарей с данными для уведомлений.
              Каждый словарь содержит: 
              - telegram_id: ID пользователя в MAX (кому отправлять)
              - assignment_id: ID задания (чтобы отметить отправку)
              - title: название задания
              - deadline: дата дедлайна
              - discipline_name: название дисциплины
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем текущую дату
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Получаем дату через days дней
        target = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Ищем задания, подходящие под все условия
        cursor.execute('''
            SELECT 
                u.user_id as telegram_id,
                a.id as assignment_id,
                a.title,
                a.deadline,
                d.name as discipline_name
            FROM assignments a
            JOIN disciplines d ON a.discipline_id = d.id
            JOIN users u ON d.user_id = u.id
            WHERE a.deadline BETWEEN ? AND ?
              AND a.status = 'active'
              AND a.notified_1day = 0
              AND u.is_active = 1
        ''', (now, target))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей для уведомлений: {e}")
        return []
    
    finally:
        conn.close()


def sync_assignments(user_id: int, disciplines_data: list) -> dict:
    """
    Синхронизирует данные из личного кабинета с базой данных.
    
    Эту функцию будет вызывать модуль парсинга (участник №2),
    после того как он успешно получил данные из личного кабинета.
    
    Функция делает следующее:
    1. Для каждой дисциплины: либо находит существующую, либо создаёт новую.
    2. Для каждого задания: либо обновляет существующее, либо создаёт новое.
    3. Возвращает статистику: сколько заданий добавлено и сколько обновлено.
    
    Параметры:
        user_id (int): внутренний ID пользователя из таблицы users.
        disciplines_data (list): список дисциплин с заданиями.
            Формат данных:
            [
                {
                    "name": "Математика",
                    "teacher": "Иванов И.И.",
                    "assignments": [
                        {
                            "title": "Домашняя работа 1",
                            "deadline": "2026-07-20 23:59:00",
                            "source_id": "12345"
                        }
                    ]
                }
            ]
    
    Возвращает:
        dict: статистика синхронизации.
              {"added": количество добавленных заданий,
               "updated": количество обновлённых заданий}
              Если произошла ошибка, возвращает {"added": 0, "updated": 0}.
    """
    
    # Инициализируем счётчики
    stats = {"added": 0, "updated": 0}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Проходим по каждой дисциплине из полученных данных
        for disc_data in disciplines_data:
            
            # Проверяем, есть ли уже такая дисциплина у пользователя
            cursor.execute(
                "SELECT id FROM disciplines WHERE user_id = ? AND name = ?",
                (user_id, disc_data["name"])
            )
            row = cursor.fetchone()
            
            if row:
                # Если дисциплина уже есть, берём её ID
                discipline_id = row["id"]
            else:
                # Если дисциплины нет, создаём новую
                cursor.execute(
                    "INSERT INTO disciplines (user_id, name, teacher) VALUES (?, ?, ?)",
                    (user_id, disc_data["name"], disc_data.get("teacher"))
                )
                discipline_id = cursor.lastrowid
            
            # Теперь обрабатываем задания внутри этой дисциплины
            for assignment in disc_data.get("assignments", []):
                
                # Проверяем, есть ли уже такое задание
                # Ищем по source_id (ID из личного кабинета)
                cursor.execute(
                    """SELECT id FROM assignments 
                       WHERE discipline_id = ? AND source_id = ?""",
                    (discipline_id, assignment.get("source_id"))
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Если задание уже есть, обновляем его
                    # (могли измениться название или дата дедлайна)
                    cursor.execute(
                        """UPDATE assignments 
                           SET title = ?, deadline = ?, last_updated = CURRENT_TIMESTAMP
                           WHERE id = ?""",
                        (assignment["title"], assignment["deadline"], existing["id"])
                    )
                    stats["updated"] += 1
                else:
                    # Если задания нет, создаём новое
                    cursor.execute(
                        """INSERT INTO assignments (discipline_id, title, deadline, source_id)
                           VALUES (?, ?, ?, ?)""",
                        (discipline_id, assignment["title"], assignment["deadline"], assignment.get("source_id"))
                    )
                    stats["added"] += 1
        
        # Сохраняем все изменения
        conn.commit()
        
    except Exception as e:
        # Если произошла ошибка, откатываем все изменения
        logger.error(f"Ошибка при синхронизации данных: {e}")
        conn.rollback()
        return {"added": 0, "updated": 0}
    
    finally:
        conn.close()
    
    return stats


# ТЕСТОВЫЙ БЛОК

# Этот блок выполняется только если запустить файл напрямую (python database.py)
# При импорте модуля в другой файл этот код не выполняется
if __name__ == '__main__':
    
    print("=" * 60)
    print("ЗАПУСК ТЕСТИРОВАНИЯ МОДУЛЯ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    # ШАГ 1: Создаём базу данных и таблицы
    print("\n[1] Создание базы данных...")
    init_db()
    print("  База данных создана успешно!")
    
    # ШАГ 2: Добавляем тестового пользователя
    print("\n[2] Добавление тестового пользователя...")
    user_id = add_user("test_user_123", "test_login", "test_pass")
    print(f"  Пользователь добавлен с ID: {user_id}")
    
    # ШАГ 3: Добавляем дисциплину
    print("\n[3] Добавление дисциплины...")
    disc_id = add_discipline(user_id, "Математика", "Иванов И.И.")
    print(f"  Дисциплина добавлена с ID: {disc_id}")
    
    # ШАГ 4: Добавляем задание
    print("\n[4] Добавление задания...")
    ass_id = add_assignment(disc_id, "Домашняя работа 1", "2026-07-20 23:59:00")
    print(f"  Задание добавлено с ID: {ass_id}")
    
    # ШАГ 5: Получаем все задания пользователя
    print("\n[5] Получение всех заданий...")
    assignments = get_assignments(user_id)
    print("  Список заданий:")
    for a in assignments:
        print(f"    - {a['discipline_name']}: {a['title']} (дедлайн: {a['deadline']})")
    
    # ШАГ 6: Получаем ближайшие задания (3 дня)
    print("\n[6] Получение ближайших заданий (3 дня)...")
    soon = get_assignments_soon(user_id, 3)
    print("  Ближайшие задания:")
    for a in soon:
        print(f"    - {a['discipline_name']}: {a['title']} (дедлайн: {a['deadline']})")
    
    # ШАГ 7: Проверяем пользователей для уведомлений
    print("\n[7] Проверка пользователей для уведомлений...")
    notifications = get_users_for_notification(1)
    print(f"  Найдено пользователей для уведомлений: {len(notifications)}")
    for n in notifications:
        print(f"    - {n['telegram_id']}: {n['discipline_name']} - {n['title']} ({n['deadline']})")
    
    # ШАГ 8: Отмечаем уведомление как отправленное
    print("\n[8] Отметка уведомления как отправленного...")
    result = mark_notification_sent(ass_id)
    print(f"  Уведомление отмечено: {result}")
    
    # ШАГ 9: Синхронизация данных (имитация данных из личного кабинета)
    print("\n[9] Тестирование синхронизации данных...")
    test_data = [
        {
            "name": "Математика",
            "teacher": "Иванов И.И.",
            "assignments": [
                {
                    "title": "Домашняя работа 1",
                    "deadline": "2026-07-21 23:59:00",  # Изменили дату
                    "source_id": "12345"
                },
                {
                    "title": "Домашняя работа 2",  # Новое задание
                    "deadline": "2026-07-25 23:59:00",
                    "source_id": "12346"
                }
            ]
        },
        {
            "name": "Физика",  # Новая дисциплина
            "teacher": "Петров П.П.",
            "assignments": [
                {
                    "title": "Лабораторная работа 1",
                    "deadline": "2026-07-22 23:59:00",
                    "source_id": "12347"
                }
            ]
        }
    ]
    
    sync_stats = sync_assignments(user_id, test_data)
    print(f"  Результат синхронизации: добавлено {sync_stats['added']}, обновлено {sync_stats['updated']}")
    
    # ШАГ 10: Проверяем итоговый список заданий
    print("\n[10] Итоговый список заданий после синхронизации...")
    final_assignments = get_assignments(user_id)
    for a in final_assignments:
        print(f"    - {a['discipline_name']}: {a['title']} (дедлайн: {a['deadline']})")
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    print("=" * 60)
