from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "openid", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_superuser")
    search_fields = ("username", "openid", "nickname")

