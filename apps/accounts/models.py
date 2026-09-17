from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "普通用户"
        ADMIN = "admin", "管理员"

    openid = models.CharField("微信 OpenID", max_length=64, unique=True, blank=True, null=True)
    nickname = models.CharField("昵称", max_length=100, blank=True)
    avatar_url = models.URLField("头像", blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)

    def save(self, *args, **kwargs):
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def is_role_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

