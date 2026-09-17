from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView

from .models import User
from .forms import WebLoginForm, WebUserRegistrationForm
from .serializers import AccountLoginSerializer, AccountRegisterSerializer, AccountProfileSerializer, UserSerializer


class AccountLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AccountLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "用户名或密码错误"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            }
        )


class AccountRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AccountRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nickname = serializer.validated_data.get("nickname") or serializer.validated_data["username"]
        avatar_url = serializer.validated_data.get("avatar_url", "")
        user = User.objects.create_user(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            nickname=nickname,
            avatar_url=avatar_url,
            role=User.Role.USER,
        )
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AccountMeView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountProfileSerializer

    def get_object(self):
        return self.request.user


class WebLoginView(FormView):
    template_name = "accounts/login.html"
    form_class = WebLoginForm

    def form_valid(self, form):
        user = authenticate(
            self.request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is None:
            form.add_error(None, "用户名或密码错误")
            return self.form_invalid(form)
        login(self.request, user)
        return redirect("/web/")


class WebRegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = WebUserRegistrationForm

    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = user.Role.USER
        user.save()
        login(self.request, user)
        return redirect("/web/")


class WebLogoutView(LogoutView):
    next_page = "/"
