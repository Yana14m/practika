"""
Модуль базы данных для MAX-бота.
Хранит пользователей, дисциплины и задания с дедлайнами.
Использует SQLite (встроен в Python).
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = 'max_bot.db'


def get_connection() -> sqlite3.Connection:
    """Подключение к БД. Возвращает строки как словари."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицы, если их нет. Вызвать один раз при запуске."""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            login TEXT,
            password TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица дисциплин
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disciplines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            teacher TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Таблица заданий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discipline_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            deadline DATETIME NOT NULL,
            status TEXT DEFAULT 'active',
            notified_1day INTEGER DEFAULT 0,
            source_id TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (discipline_id) REFERENCES disciplines(id) ON DELETE CASCADE
        )
    ''')

    # Индексы для ускорения
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_deadline ON assignments(deadline)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status)')

    conn.commit()
    conn.close()
    logger.info("База данных и таблицы созданы.")


# ПОЛЬЗОВАТЕЛИ

def add_user(user_id: str, login: str = '', password: str = '') -> int:
    """Добавляет пользователя. Возвращает его ID или -1 при ошибке."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, login, password) VALUES (?, ?, ?)",
            (user_id, login, password)
        )
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row['id'] if row else -1
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        return -1
    finally:
        conn.close()


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Получает данные пользователя. Возвращает словарь или None."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        return None
    finally:
        conn.close()


def update_user_password(user_id: str, new_password: str) -> bool:
    """Обновляет пароль пользователя. Возвращает True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET password = ? WHERE user_id = ?",
            (new_password, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при обновлении пароля: {e}")
        return False
    finally:
        conn.close()


def delete_user(user_id: str) -> bool:
    """Мягкое удаление (is_active = 0). Возвращает True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        return False
    finally:
        conn.close()


# ДИСЦИПЛИНЫ

def add_discipline(user_id: int, name: str, teacher: str = None) -> int:
    """Добавляет дисциплину. Возвращает её ID или -1 при ошибке."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO disciplines (user_id, name, teacher) VALUES (?, ?, ?)",
            (user_id, name, teacher)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при добавлении дисциплины: {e}")
        return -1
    finally:
        conn.close()


def get_disciplines(user_id: int) -> List[Dict[str, Any]]:
    """Получает все дисциплины пользователя. Возвращает список словарей."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM disciplines WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении дисциплин: {e}")
        return []
    finally:
        conn.close()


def get_discipline_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """Ищет дисциплину по названию. Возвращает словарь или None."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM disciplines WHERE user_id = ? AND name = ?",
            (user_id, name)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при поиске дисциплины: {e}")
        return None
    finally:
        conn.close()


# ЗАДАНИЯ

def add_assignment(discipline_id: int, title: str, deadline: str, source_id: str = None) -> int:
    """Добавляет задание. Возвращает его ID или -1 при ошибке."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
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
        logger.error(f"Ошибка при добавлении задания: {e}")
        return -1
    finally:
        conn.close()


def get_assignments(user_id: int) -> List[Dict[str, Any]]:
    """
    Получает все задания пользователя с названиями дисциплин.
    Сортировка по дедлайну. Возвращает список словарей.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT 
                a.id, a.title, a.deadline, a.status, a.notified_1day,
                d.name as discipline_name
            FROM assignments a
            JOIN disciplines d ON a.discipline_id = d.id
            WHERE d.user_id = ?
            ORDER BY a.deadline ASC
        ''', (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении заданий: {e}")
        return []
    finally:
        conn.close()


def get_assignments_soon(user_id: int, days: int = 3) -> List[Dict[str, Any]]:
    """Получает задания с дедлайном в ближайшие N дней."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        future = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            SELECT 
                a.id, a.title, a.deadline,
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
    """Получает задание по ID. Возвращает словарь или None."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении задания: {e}")
        return None
    finally:
        conn.close()


# УВЕДОМЛЕНИЯ

def mark_notification_sent(assignment_id: int) -> bool:
    """Отмечает, что уведомление отправлено. Возвращает True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE assignments SET notified_1day = 1 WHERE id = ?",
            (assignment_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка при отметке уведомления: {e}")
        return False
    finally:
        conn.close()


def get_users_for_notification(days: int = 1) -> List[Dict[str, Any]]:
    """
    Получает пользователей для уведомлений.
    Условия: дедлайн через days дней, уведомление не отправлено, задание активно, пользователь активен.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        target = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
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


# СИНХРОНИЗАЦИЯ

def sync_assignments(user_id: int, disciplines_data: list) -> dict:
    """
    Синхронизирует данные из личного кабинета с БД.
    disciplines_data = [
        {"name": "Математика", "teacher": "Иванов", "assignments": [
            {"title": "ДЗ 1", "deadline": "2026-07-20 23:59:00", "source_id": "123"}
        ]}
    ]
    Возвращает {"added": n, "updated": n}
    """
    stats = {"added": 0, "updated": 0}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for disc_data in disciplines_data:
            cursor.execute(
                "SELECT id FROM disciplines WHERE user_id = ? AND name = ?",
                (user_id, disc_data["name"])
            )
            row = cursor.fetchone()
            if row:
                discipline_id = row["id"]
            else:
                cursor.execute(
                    "INSERT INTO disciplines (user_id, name, teacher) VALUES (?, ?, ?)",
                    (user_id, disc_data["name"], disc_data.get("teacher"))
                )
                discipline_id = cursor.lastrowid
            for assignment in disc_data.get("assignments", []):
                cursor.execute(
                    """SELECT id FROM assignments 
                       WHERE discipline_id = ? AND source_id = ?""",
                    (discipline_id, assignment.get("source_id"))
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """UPDATE assignments 
                           SET title = ?, deadline = ?, last_updated = CURRENT_TIMESTAMP
                           WHERE id = ?""",
                        (assignment["title"], assignment["deadline"], existing["id"])
                    )
                    stats["updated"] += 1
                else:
                    cursor.execute(
                        """INSERT INTO assignments (discipline_id, title, deadline, source_id)
                           VALUES (?, ?, ?, ?)""",
                        (discipline_id, assignment["title"], assignment["deadline"], assignment.get("source_id"))
                    )
                    stats["added"] += 1
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}")
        conn.rollback()
        return {"added": 0, "updated": 0}
    finally:
        conn.close()
    return stats


if __name__ == '__main__':
    print("Запуск тестирования модуля базы данных...")
    init_db()
    user_id = add_user("test_user_123", "test_login", "test_pass")
    print(f"Пользователь добавлен с ID: {user_id}")
    disc_id = add_discipline(user_id, "Математика", "Иванов И.И.")
    print(f"Дисциплина добавлена с ID: {disc_id}")
    ass_id = add_assignment(disc_id, "Домашняя работа 1", "2026-07-20 23:59:00")
    print(f"Задание добавлено с ID: {ass_id}")
    assignments = get_assignments(user_id)
    print("Список заданий:")
    for a in assignments:
        print(f"  - {a['discipline_name']}: {a['title']} (дедлайн: {a['deadline']})")
    soon = get_assignments_soon(user_id, 3)
    print("Ближайшие задания (3 дня):")
    for a in soon:
        print(f"  - {a['discipline_name']}: {a['title']} (дедлайн: {a['deadline']})")
    notifications = get_users_for_notification(1)
    print(f"Пользователей для уведомлений: {len(notifications)}")
    for n in notifications:
        print(f"  - {n['telegram_id']}: {n['discipline_name']} - {n['title']} ({n['deadline']})")
    result = mark_notification_sent(ass_id)
    print(f"Уведомление отмечено: {result}")
    print("Тестирование завершено!")
