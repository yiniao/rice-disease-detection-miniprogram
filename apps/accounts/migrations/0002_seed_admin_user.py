"""创建初始管理员账号。

密码不再硬编码在迁移文件里(仓库是公开的,硬编码默认口令等于给所有人留后门)。
改为从环境变量读取,未配置时跳过创建,由部署者自行执行:

    python manage.py createsuperuser

可用环境变量:
    DJANGO_ADMIN_USERNAME  默认 admin
    DJANGO_ADMIN_PASSWORD  未设置则跳过创建
    DJANGO_ADMIN_NICKNAME  默认 管理员
"""

import os

from django.contrib.auth.hashers import make_password
from django.db import migrations

DEFAULT_USERNAME = "admin"
DEFAULT_NICKNAME = "管理员"


def create_default_admin(apps, schema_editor):
    password = os.getenv("DJANGO_ADMIN_PASSWORD", "").strip()
    if not password:
        print(
            "跳过创建默认管理员:未设置 DJANGO_ADMIN_PASSWORD。"
            "如需初始管理员,请设置该环境变量后重跑迁移,或执行 python manage.py createsuperuser。"
        )
        return

    User = apps.get_model("accounts", "User")
    User.objects.update_or_create(
        username=os.getenv("DJANGO_ADMIN_USERNAME", DEFAULT_USERNAME).strip() or DEFAULT_USERNAME,
        defaults={
            "password": make_password(password),
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "nickname": os.getenv("DJANGO_ADMIN_NICKNAME", DEFAULT_NICKNAME).strip() or DEFAULT_NICKNAME,
        },
    )


def remove_default_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    username = os.getenv("DJANGO_ADMIN_USERNAME", DEFAULT_USERNAME).strip() or DEFAULT_USERNAME
    User.objects.filter(username=username).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_admin, reverse_code=remove_default_admin),
    ]
