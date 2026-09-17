import importlib
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()

# 迁移模块文件名以数字开头,只能用 importlib 按字符串导入
seed_admin_migration = importlib.import_module("apps.accounts.migrations.0002_seed_admin_user")


class AccountLoginTests(TestCase):
    def test_username_password_login_returns_token(self):
        User.objects.create_user(username="farmer", password="secret123")
        client = APIClient()
        response = client.post(
            "/api/auth/login/",
            {"username": "farmer", "password": "secret123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["user"]["username"], "farmer")

    def test_invalid_password_is_rejected(self):
        client = APIClient()
        User.objects.create_user(username="farmer", password="secret123")
        response = client.post("/api/auth/login/", {"username": "farmer", "password": "bad"}, format="json")
        self.assertEqual(response.status_code, 400)


class AccountRegisterTests(TestCase):
    def test_register_returns_token_and_user(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {
                "username": "newfarmer",
                "password": "secret123",
                "nickname": "稻农",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["user"]["username"], "newfarmer")
        self.assertEqual(response.data["user"]["nickname"], "稻农")

    def test_register_rejects_duplicate_username(self):
        client = APIClient()
        User.objects.create_user(username="farmer", password="secret123")
        response = client.post(
            "/api/auth/register/",
            {
                "username": "farmer",
                "password": "secret123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class AccountProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="farmer", password="secret123", nickname="稻农")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_me_endpoint_returns_current_user(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "farmer")
        self.assertEqual(response.data["nickname"], "稻农")

    def test_me_endpoint_updates_username_and_password(self):
        response = self.client.patch(
            "/api/auth/me/",
            {
                "username": "farmer_new",
                "nickname": "新稻农",
                "old_password": "secret123",
                "new_password": "newsecret123",
                "confirm_password": "newsecret123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "farmer_new")
        self.assertEqual(self.user.nickname, "新稻农")
        self.assertTrue(self.user.check_password("newsecret123"))

    def test_me_endpoint_rejects_duplicate_username(self):
        User.objects.create_user(username="other", password="secret123")
        response = self.client.patch("/api/auth/me/", {"username": "other"}, format="json")
        self.assertEqual(response.status_code, 400)


class DefaultAdminSeedTests(TestCase):
    """默认管理员由环境变量驱动:未提供 DJANGO_ADMIN_PASSWORD 时不创建任何账号。"""

    @staticmethod
    def _fake_apps():
        """迁移函数只用到 apps.get_model,这里用真实模型代替历史模型即可。"""

        class _Apps:
            @staticmethod
            def get_model(app_label, model_name):
                assert (app_label, model_name) == ("accounts", "User")
                return User

        return _Apps()

    def test_no_admin_created_without_password(self):
        os.environ.pop("DJANGO_ADMIN_PASSWORD", None)
        seed_admin_migration.create_default_admin(self._fake_apps(), None)
        self.assertFalse(User.objects.exists())

    def test_admin_created_from_environment(self):
        env = {
            "DJANGO_ADMIN_PASSWORD": "s3cret-from-env",
            "DJANGO_ADMIN_USERNAME": "boss",
            "DJANGO_ADMIN_NICKNAME": "站长",
        }
        with patch.dict(os.environ, env):
            seed_admin_migration.create_default_admin(self._fake_apps(), None)

        user = User.objects.get(username="boss")
        self.assertTrue(user.check_password("s3cret-from-env"))
        self.assertEqual(user.nickname, "站长")
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_hardcoded_default_password_is_gone(self):
        """回归守卫:代码里不允许再出现 admin/admin 这种默认口令。"""
        os.environ.pop("DJANGO_ADMIN_PASSWORD", None)
        seed_admin_migration.create_default_admin(self._fake_apps(), None)
        self.assertFalse(User.objects.filter(username="admin").exists())
