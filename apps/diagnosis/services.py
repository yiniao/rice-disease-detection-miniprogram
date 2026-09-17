import time
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from PIL import UnidentifiedImageError

from apps.common.file_names import sanitize_filename
from apps.common.image_utils import encode_bytes_to_base64
from apps.ai_analysis.models import AdviceRecord
from apps.ai_analysis.services import AdviceService

from .models import DetectionRecord, DetectionResult, ModelConfig


class InferenceServiceError(Exception):
    pass


def _fallback_config():
    return {
        "backend": settings.MODEL_BACKEND,
        "name": settings.DEFAULT_MODEL_NAME,
        "version": settings.DEFAULT_MODEL_VERSION,
        "weights_path": settings.ULTRALYTICS_WEIGHTS_PATH,
        "device": settings.ULTRALYTICS_DEVICE,
        "class_names": settings.DEFAULT_MODEL_CLASS_NAMES,
        "confidence_threshold": 0.25,
        "input_size": 640,
    }


def get_active_model_config():
    config = ModelConfig.objects.filter(is_active=True).first()
    if config:
        return {
            "backend": config.backend,
            "name": config.name,
            "version": config.version,
            "weights_path": config.weights_path,
            "device": settings.ULTRALYTICS_DEVICE,
            "class_names": config.class_names or settings.DEFAULT_MODEL_CLASS_NAMES,
            "confidence_threshold": config.confidence_threshold,
            "input_size": config.input_size,
        }
    return _fallback_config()


class ModelInferenceService:
    _cached_sessions = {}

    @classmethod
    def predict(cls, image, config):
        if config["backend"] in {ModelConfig.Backend.ONNX, ModelConfig.Backend.ULTRALYTICS}:
            return cls._predict_onnx(image, config)
        return cls._predict_mock(image, config)

    @classmethod
    def _predict_mock(cls, image, config):
        width, height = image.size
        label = config["class_names"][0] if config["class_names"] else "稻瘟病"
        return [
            {
                "label": label,
                "confidence": 0.92,
                "xmin": round(width * 0.18, 2),
                "ymin": round(height * 0.22, 2),
                "xmax": round(width * 0.74, 2),
                "ymax": round(height * 0.68, 2),
            }
        ]

    @classmethod
    def _letterbox(cls, image, new_shape=640, color=(114, 114, 114)):
        width, height = image.size
        scale = min(new_shape / width, new_shape / height)
        resized_width = int(round(width * scale))
        resized_height = int(round(height * scale))
        resized = image.resize((resized_width, resized_height), Image.Resampling.BILINEAR)
        canvas = Image.new("RGB", (new_shape, new_shape), color)
        pad_x = (new_shape - resized_width) // 2
        pad_y = (new_shape - resized_height) // 2
        canvas.paste(resized, (pad_x, pad_y))
        return canvas, scale, pad_x, pad_y

    @classmethod
    def _load_onnx_session(cls, weights_path):
        session = cls._cached_sessions.get(weights_path)
        if session is None:
            import onnxruntime as ort

            session = ort.InferenceSession(weights_path, providers=["CPUExecutionProvider"])
            cls._cached_sessions[weights_path] = session
        return session

    @classmethod
    def _predict_onnx(cls, image, config):
        try:
            import numpy as np
        except ImportError as exc:
            raise InferenceServiceError("缺少 ONNX 推理依赖。") from exc

        weights_path = config["weights_path"] or settings.ULTRALYTICS_WEIGHTS_PATH
        if not weights_path:
            raise InferenceServiceError("缺少本地模型权重路径配置。")
        if not Path(weights_path).exists():
            raise InferenceServiceError(f"模型权重不存在：{weights_path}")

        session = cls._load_onnx_session(weights_path)
        input_meta = session.get_inputs()[0]
        input_name = input_meta.name
        input_size = int(config.get("input_size") or 640)

        letterboxed, scale, pad_x, pad_y = cls._letterbox(image, input_size)
        array = np.asarray(letterboxed).astype(np.float32) / 255.0
        array = np.transpose(array, (2, 0, 1))[None]

        outputs = session.run(None, {input_name: array})
        prediction = np.asarray(outputs[0])
        rows = prediction[0] if prediction.ndim == 3 else prediction
        outputs = []
        names = config["class_names"] or settings.DEFAULT_MODEL_CLASS_NAMES

        for row in rows:
            if len(row) < 6:
                continue
            xmin, ymin, xmax, ymax, confidence, cls_idx = [float(value) for value in row[:6]]
            if confidence < config["confidence_threshold"]:
                continue
            xmin = max((xmin - pad_x) / scale, 0)
            ymin = max((ymin - pad_y) / scale, 0)
            xmax = min((xmax - pad_x) / scale, image.size[0])
            ymax = min((ymax - pad_y) / scale, image.size[1])
            if xmax <= xmin or ymax <= ymin:
                continue
            cls_idx = int(cls_idx)
            outputs.append(
                {
                    "label": names[cls_idx] if 0 <= cls_idx < len(names) else str(cls_idx),
                    "confidence": round(confidence, 4),
                    "xmin": round(xmin, 2),
                    "ymin": round(ymin, 2),
                    "xmax": round(xmax, 2),
                    "ymax": round(ymax, 2),
                }
            )
        return sorted(outputs, key=lambda item: item["confidence"], reverse=True)


def _load_font():
    if settings.VIS_FONT_PATH:
        try:
            return ImageFont.truetype(settings.VIS_FONT_PATH, 20)
        except OSError:
            pass
    return ImageFont.load_default()


def render_visualized_image(image, detections):
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = _load_font()

    for item in detections:
        box = [item["xmin"], item["ymin"], item["xmax"], item["ymax"]]
        draw.rectangle(box, outline="#34a853", width=4)
        text = f'{item["label"]} {item["confidence"]:.2f}'
        text_box = draw.textbbox((box[0], max(box[1] - 24, 0)), text, font=font)
        draw.rectangle(text_box, fill="#34a853")
        draw.text((text_box[0] + 4, text_box[1] + 2), text, fill="white", font=font)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


class DetectionPipelineService:
    @classmethod
    def run(cls, user, image_file, *, original_filename=""):
        if hasattr(image_file, "seek"):
            image_file.seek(0)
        image_bytes = image_file.read()
        original_base64 = encode_bytes_to_base64(image_bytes)
        fallback_name = getattr(image_file, "name", "") or original_filename or "image.jpg"
        record = DetectionRecord.objects.create(
            user=user,
            original_image=original_base64,
            original_filename=sanitize_filename(original_filename or fallback_name),
            status=DetectionRecord.Status.PENDING,
        )
        start = time.perf_counter()
        try:
            try:
                with Image.open(BytesIO(image_bytes)) as source_image:
                    image = source_image.convert("RGB")
                    record.image_width, record.image_height = image.size
            except (UnidentifiedImageError, OSError) as exc:
                raise ValueError("请上传有效图片，文件无法识别或已损坏。") from exc

            detections = ModelInferenceService.predict(image, get_active_model_config())
            for item in detections:
                DetectionResult.objects.create(record=record, **item)

            visualized_bytes = render_visualized_image(image.copy(), detections)
            record.visualized_image = encode_bytes_to_base64(visualized_bytes)

            advice_payload = AdviceService.generate(detections)
            AdviceRecord.objects.update_or_create(
                record=record,
                defaults={
                    "source": advice_payload["source"],
                    "prompt_excerpt": advice_payload["prompt"][:4000],
                    "response_text": advice_payload["text"],
                    "raw_response": advice_payload["raw"],
                    "status": advice_payload["status"],
                },
            )

            config = get_active_model_config()
            record.status = DetectionRecord.Status.SUCCESS
            record.model_name = config["name"]
            record.model_version = config["version"]
            record.duration_ms = int((time.perf_counter() - start) * 1000)
            record.error_message = ""
            record.save(
                update_fields=[
                    "visualized_image",
                    "original_filename",
                    "status",
                    "model_name",
                    "model_version",
                    "duration_ms",
                    "image_width",
                    "image_height",
                    "error_message",
                    "updated_at",
                ]
            )
        except Exception as exc:
            config = get_active_model_config()
            record.status = DetectionRecord.Status.FAILED
            record.model_name = config["name"]
            record.model_version = config["version"]
            record.duration_ms = int((time.perf_counter() - start) * 1000)
            record.error_message = str(exc)
            record.save(
                update_fields=[
                    "status",
                    "model_name",
                    "model_version",
                    "duration_ms",
                    "image_width",
                    "image_height",
                    "original_filename",
                    "error_message",
                    "updated_at",
                ]
            )
        return record
