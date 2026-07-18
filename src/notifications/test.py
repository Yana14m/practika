"""
Тесты для database.py и notifications.py.

Запуск:
    python -m pytest src/notifications/test.py
    python -m unittest src.notifications.test
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import src.db.database as database
from src.db.database import (
    add_assignment,
    add_discipline,
    add_user,
    delete_user,
    get_assignment_by_id,
    get_assignments,
    get_assignments_soon,
    get_discipline_by_name,
    get_disciplines,
    get_user,
    get_users_for_notification,
    init_db,
    mark_notification_sent,
    sync_assignments,
    update_user_credentials,
    update_user_password,
)
from src.notifications.notifications import check_and_notify, setup_scheduler


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        database.DB_NAME = self._tmp.name
        init_db()

        self.db_user_id = add_user("test_user_123", "test_login", "test_password")
        self.disc_id = add_discipline(self.db_user_id, "Математика", "Иванов И.И.")
        deadline_2days = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        self.assignment_id = add_assignment(
            self.disc_id, "Лабораторная работа №1", deadline_2days, "source_123"
        )

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_add_user(self):
        new_id = add_user("test_user_456", "login2", "password2")
        self.assertNotEqual(new_id, -1)
        user = get_user("test_user_456")
        self.assertIsNotNone(user)
        self.assertEqual(user["login"], "login2")
        self.assertEqual(user["password"], "password2")
        self.assertEqual(user["is_active"], 1)

    def test_get_user_not_found(self):
        user = get_user("unknown_user_999")
        self.assertIsNone(user)

    def test_update_user_password(self):
        result = update_user_password("test_user_123", "new_secure_password")
        self.assertTrue(result)
        user = get_user("test_user_123")
        self.assertEqual(user["password"], "new_secure_password")

    def test_update_user_credentials(self):
        result = update_user_credentials("test_user_123", "new_login", "new_password")
        self.assertTrue(result)
        user = get_user("test_user_123")
        self.assertEqual(user["login"], "new_login")
        self.assertEqual(user["password"], "new_password")

    def test_delete_user(self):
        result = delete_user("test_user_123")
        self.assertTrue(result)
        user = get_user("test_user_123")
        self.assertEqual(user["is_active"], 0)

    def test_add_discipline(self):
        new_disc_id = add_discipline(self.db_user_id, "Физика", "Петров П.П.")
        self.assertNotEqual(new_disc_id, -1)
        disciplines = get_disciplines(self.db_user_id)
        self.assertEqual(len(disciplines), 2)
        physics = get_discipline_by_name(self.db_user_id, "Физика")
        self.assertIsNotNone(physics)
        self.assertEqual(physics["teacher"], "Петров П.П.")

    def test_add_assignment(self):
        new_ass_id = add_assignment(
            self.disc_id, "Курсовая работа №1", "2026-12-31 23:59:00", "source_456"
        )
        self.assertNotEqual(new_ass_id, -1)
        assignments = get_assignments(self.db_user_id)
        self.assertEqual(len(assignments), 2)

    def test_get_assignments_soon(self):
        soon = get_assignments_soon(self.db_user_id, days=3)
        self.assertEqual(len(soon), 1)
        self.assertEqual(soon[0]["title"], "Лабораторная работа №1")

    def test_get_assignments_soon_excludes_far_deadline(self):
        deadline_far = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        add_assignment(self.disc_id, "Задание далёкое", deadline_far, "source_789")
        soon = get_assignments_soon(self.db_user_id, days=3)
        self.assertEqual(len(soon), 1)

    def test_mark_notification_sent(self):
        result = mark_notification_sent(self.assignment_id)
        self.assertTrue(result)
        ass = get_assignment_by_id(self.assignment_id)
        self.assertEqual(ass["notified_1day"], 1)

    def test_get_users_for_notification(self):
        items = get_users_for_notification(days=3)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["telegram_id"], "test_user_123")

    def test_get_users_for_notification_after_mark(self):
        mark_notification_sent(self.assignment_id)
        items = get_users_for_notification(days=3)
        self.assertEqual(len(items), 0)

    def test_sync_assignments_add(self):
        data = [
            {
                "name": "Новая дисциплина",
                "teacher": "Сидоров С.С.",
                "assignments": [
                    {
                        "title": "Задание №1: Реферат",
                        "deadline": "2026-12-01 23:59:00",
                        "source_id": "sync_1",
                    }
                ],
            }
        ]
        result = sync_assignments(self.db_user_id, data)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["updated"], 0)

    def test_sync_assignments_update(self):
        data = [
            {
                "name": "Математика",
                "teacher": "Иванов И.И.",
                "assignments": [
                    {
                        "title": "Лабораторная работа №1 (обновлено)",
                        "deadline": "2026-12-01 23:59:00",
                        "source_id": "source_123",
                    }
                ],
            }
        ]
        result = sync_assignments(self.db_user_id, data)
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["updated"], 1)


class TestNotifications(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        database.DB_NAME = self._tmp.name
        init_db()
        user_id = add_user("123456789", "login1", "pass1")
        disc_id = add_discipline(user_id, "Физика", "Учитель Т.Т.")
        deadline_soon = (datetime.now() + timedelta(hours=20)).strftime("%Y-%m-%d %H:%M:%S")
        self.assignment_id = add_assignment(disc_id, "Срочное задание", deadline_soon, "src_n1")

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    async def test_check_and_notify_sends_message(self):
        mock_bot = AsyncMock()
        await check_and_notify(mock_bot)
        mock_bot.send_message.assert_called_once()
        user_id_arg, text_arg = mock_bot.send_message.call_args[0]
        self.assertEqual(user_id_arg, 123456789)
        self.assertIn("Физика", text_arg)

    async def test_check_and_notify_marks_sent(self):
        mock_bot = AsyncMock()
        await check_and_notify(mock_bot)
        ass = get_assignment_by_id(self.assignment_id)
        self.assertEqual(ass["notified_1day"], 1)

    async def test_check_and_notify_no_double_send(self):
        mock_bot = AsyncMock()
        await check_and_notify(mock_bot)
        await check_and_notify(mock_bot)
        self.assertEqual(mock_bot.send_message.call_count, 1)

    async def test_check_and_notify_no_assignments(self):
        # create a fresh db with no upcoming assignments
        tmp2 = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp2.close()
        database.DB_NAME = tmp2.name
        try:
            init_db()
            add_user("111111111", "l", "p")
            mock_bot = AsyncMock()
            await check_and_notify(mock_bot)
            mock_bot.send_message.assert_not_called()
        finally:
            os.unlink(tmp2.name)

    def test_setup_scheduler_job(self):
        mock_bot = MagicMock()
        scheduler = setup_scheduler(mock_bot)
        self.assertIsNotNone(scheduler)
        jobs = scheduler.get_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, "notify_job")


if __name__ == "__main__":
    unittest.main()
