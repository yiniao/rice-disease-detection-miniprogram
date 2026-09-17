from django.conf import settings
from django.core.management.base import BaseCommand

from apps.diagnosis.models import ModelConfig


class Command(BaseCommand):
    help = "根据当前环境变量和仓库内默认权重创建/更新模型配置。"

    def add_arguments(self, parser):
        parser.add_argument("--activate", action="store_true", help="创建后直接设为启用状态。")

    def handle(self, *args, **options):
        if not settings.ULTRALYTICS_WEIGHTS_PATH:
            self.stderr.write(self.style.ERROR("未找到默认权重路径，请先设置 ULTRALYTICS_WEIGHTS_PATH。"))
            return

        config, created = ModelConfig.objects.update_or_create(
            name=settings.DEFAULT_MODEL_NAME,
            version=settings.DEFAULT_MODEL_VERSION,
            defaults={
                "backend": ModelConfig.Backend.ONNX,
                "weights_path": settings.ULTRALYTICS_WEIGHTS_PATH,
                "class_names": settings.DEFAULT_MODEL_CLASS_NAMES,
                "confidence_threshold": 0.25,
                "input_size": 640,
                "is_active": options["activate"],
            },
        )
        if options["activate"]:
            ModelConfig.objects.exclude(pk=config.pk).update(is_active=False)

        message = "已创建" if created else "已更新"
        self.stdout.write(
            self.style.SUCCESS(
                f"{message}模型配置：{config.name} {config.version} -> {config.weights_path}"
            )
        )
