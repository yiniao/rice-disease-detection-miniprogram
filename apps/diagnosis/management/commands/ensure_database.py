import pymysql
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the configured MySQL database if it does not exist."

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        if db["ENGINE"] != "django.db.backends.mysql":
            self.stdout.write(self.style.NOTICE("Not using MySQL, skipping database creation."))
            return

        name = db["NAME"]
        host = db.get("HOST", "127.0.0.1") or "127.0.0.1"
        port = int(db.get("PORT", "3306") or "3306")
        user = db.get("USER", "root") or "root"
        password = db.get("PASSWORD", "") or ""

        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            self.stdout.write(self.style.SUCCESS(f"Database '{name}' is ready."))
        finally:
            conn.close()
