FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=rice_guard.settings
ENV PORT=8080

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py /app/
COPY data.yaml /app/
COPY rice_guard /app/rice_guard
COPY apps /app/apps
COPY 0712_null/weights/best.onnx /app/0712_null/weights/best.onnx

# 注意:不要 COPY .env 进镜像。
# 数据库密码、SECRET_KEY、API Key 应在云托管控制台以环境变量注入,
# 打进镜像会随镜像分发给任何能拉取镜像的人。

RUN python manage.py collectstatic --noinput || true

EXPOSE 8080

CMD sh -c "python manage.py ensure_database && python manage.py migrate --noinput && exec gunicorn rice_guard.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 120"
