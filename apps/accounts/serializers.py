from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class AccountLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)


class AccountRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True, min_length=8)
    nickname = serializers.CharField(max_length=100, required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "nickname", "avatar_url", "role")


class AccountProfileSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "nickname",
            "avatar_url",
            "role",
            "old_password",
            "new_password",
            "confirm_password",
        )
        read_only_fields = ("id", "role")

    def validate_username(self, value):
        queryset = User.objects.exclude(pk=getattr(self.instance, "pk", None))
        if queryset.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate(self, attrs):
        new_password = attrs.get("new_password") or ""
        confirm_password = attrs.get("confirm_password") or ""
        old_password = attrs.get("old_password") or ""

        if new_password or confirm_password or old_password:
            if not old_password:
                raise serializers.ValidationError({"old_password": "修改密码时需要填写当前密码"})
            if not new_password:
                raise serializers.ValidationError({"new_password": "请输入新密码"})
            if new_password != confirm_password:
                raise serializers.ValidationError({"confirm_password": "两次输入的新密码不一致"})
            if not self.instance.check_password(old_password):
                raise serializers.ValidationError({"old_password": "当前密码不正确"})
            try:
                validate_password(new_password, user=self.instance)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"new_password": list(error.messages)})

        return attrs

    def update(self, instance, validated_data):
        new_password = validated_data.pop("new_password", "")
        validated_data.pop("confirm_password", None)
        validated_data.pop("old_password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if new_password:
            instance.set_password(new_password)

        instance.save()
        return instance
