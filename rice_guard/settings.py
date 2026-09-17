import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _default_weights_path():
    for candidate in [
        BASE_DIR / "0712_null" / "weights" / "best.onnx",
        BASE_DIR / "0712_null" / "weights" / "best.pt",
    ]:
        if candidate.exists():
            return str(candidate)
    return ""


def _env_or_default(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def _split_host_and_port(host_value, default_port="3306"):
    host = (host_value or "").strip()
    if not host:
        return "", default_port
    if host.startswith("[") and "]:" in host:
        host, port = host.rsplit("]:", 1)
        return host.lstrip("["), port or default_port
    if ":" in host and host.count(":") == 1:
        host, port = host.rsplit(":", 1)
        return host.strip(), port.strip() or default_port
    return host, default_port


def _build_database_config():
    # 数据库凭据一律从环境变量读取,不要写进源码 —— 本仓库是公开的。
    # 云托管的数据库地址在不同环境里不同,因此 host 同时兼容 MYSQL_HOST 与 MYSQL_ADDRESS。
    mysql_name = _env_or_default("MYSQL_DATABASE", "rice_guard")
    mysql_user = _env_or_default("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_host_raw = (
        os.getenv("MYSQL_HOST", "").strip()
        or os.getenv("MYSQL_ADDRESS", "").strip()
    )
    mysql_host, mysql_port = _split_host_and_port(mysql_host_raw, os.getenv("MYSQL_PORT", "3306").strip() or "3306")

    if mysql_host:
        return {
            "default": {
                "ENGINE": "django.db.backends.mysql",
                "NAME": mysql_name or "rice_guard",
                "USER": mysql_user or "root",
                "PASSWORD": mysql_password,
                "HOST": mysql_host or "127.0.0.1",
                "PORT": mysql_port,
                "OPTIONS": {
                    "charset": "utf8mb4",
                    "connect_timeout": 5,
                    "read_timeout": 5,
                    "write_timeout": 5,
                },
            }
        }

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


def _load_default_class_names():
    env_value = os.getenv("DEFAULT_MODEL_CLASS_NAMES")
    if env_value and env_value.strip():
        return [item.strip() for item in env_value.split(",") if item.strip()]

    data_yaml = BASE_DIR / "data.yaml"
    if not data_yaml.exists():
        return ["healthy", "brown_spot", "leaf_scald", "leaf_blast", "bacterial_leaf_blight", "leaf_smut", "narrow_brown_spot", "not_leaf"]

    class_names = []
    in_names_block = False
    for raw_line in data_yaml.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped == "names:":
            in_names_block = True
            continue
        if not in_names_block:
            continue
        if not stripped:
            continue
        if ":" not in stripped:
            break
        _, value = stripped.split(":", 1)
        class_names.append(value.strip())
    return class_names or ["healthy", "brown_spot", "leaf_scald", "leaf_blast", "bacterial_leaf_blight", "leaf_smut", "narrow_brown_spot", "not_leaf"]

# 生产环境必须由环境变量提供 SECRET_KEY。这里的默认值仅供本地开发,以 django-insecure-
# 开头以便一眼看出它是占位值、绝不能用于线上。
SECRET_KEY = _env_or_default("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG = _env_or_default("DJANGO_DEBUG", "False").strip().lower() in {"1", "true", "yes", "on"}

# 逗号分隔,例如 DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,example.com
# 部署到云托管时必须把公网域名加进来,否则请求会被拒绝。
ALLOWED_HOSTS = [
    host.strip()
    for host in _env_or_default("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.accounts",
    "apps.ai_analysis",
    "apps.dashboard",
    "apps.dataset",
    "apps.diagnosis",
    "apps.web_portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "rice_guard.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend_web" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "rice_guard.wsgi.application"
ASGI_APPLICATION = "rice_guard.asgi.application"

DATABASES = _build_database_config()

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/web/"
LOGOUT_REDIRECT_URL = "/"
ENABLE_WEB_FRONTEND = _env_or_default("ENABLE_WEB_FRONTEND", "True").strip().lower() in {"1", "true", "yes", "on"}

WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

MODEL_BACKEND = _env_or_default("MODEL_BACKEND", "onnx")
DEFAULT_MODEL_NAME = _env_or_default("DEFAULT_MODEL_NAME", "rice-pest-detector")
DEFAULT_MODEL_VERSION = _env_or_default("DEFAULT_MODEL_VERSION", "v1")
DEFAULT_MODEL_CLASS_NAMES = _load_default_class_names()
ULTRALYTICS_WEIGHTS_PATH = _env_or_default("ULTRALYTICS_WEIGHTS_PATH", _default_weights_path())
ULTRALYTICS_DEVICE = _env_or_default("ULTRALYTICS_DEVICE", "cpu")
VIS_FONT_PATH = os.getenv("VIS_FONT_PATH", "")
