from collections import Counter
import json
from urllib.request import Request, urlopen

from django.conf import settings

from .models import AdviceRecord


class AdviceServiceError(Exception):
    pass


def build_detection_summary(detections):
    counter = Counter(item["label"] for item in detections)
    lines = [
        f"{label}: {count} 处，最高置信度 {max(x['confidence'] for x in detections if x['label'] == label):.2f}"
        for label, count in counter.items()
    ]
    return "\n".join(lines)


class AdviceService:
    @classmethod
    def generate(cls, detections):
        if not detections:
            text = "未识别到明确病虫害。建议重新拍摄清晰叶片/穗部图片，或由农技人员进行人工复核。"
            return {
                "status": AdviceRecord.Status.FALLBACK,
                "source": AdviceRecord.Source.LOCAL_FALLBACK,
                "text": text,
                "raw": {"source": "empty-detection"},
                "prompt": "",
            }

        summary = build_detection_summary(detections)
        prompt = (
            "你是一名水稻病虫害植保专家。根据检测结果生成简洁的中文建议。\n"
            f"检测摘要：\n{summary}\n\n"
            "请按以下结构输出：\n"
            "1. 病虫害概述\n"
            "2. 可能影响\n"
            "3. 防治建议\n"
            "4. 注意事项\n"
            "补充要求：内容务实，不夸大结论，最后追加“结果仅供参考”。"
        )

        if not settings.DEEPSEEK_API_KEY:
            return {
                "status": AdviceRecord.Status.FALLBACK,
                "source": AdviceRecord.Source.LOCAL_FALLBACK,
                "text": cls._fallback_advice(detections),
                "raw": {"source": "local-fallback", "summary": summary},
                "prompt": prompt,
            }

        try:
            raw, text = cls._call_deepseek(prompt)
            return {
                "status": AdviceRecord.Status.SUCCESS,
                "source": AdviceRecord.Source.DEEPSEEK,
                "text": text,
                "raw": raw,
                "prompt": prompt,
            }
        except AdviceServiceError as exc:
            return {
                "status": AdviceRecord.Status.FALLBACK,
                "source": AdviceRecord.Source.LOCAL_FALLBACK,
                "text": f"{cls._fallback_advice(detections)}\n\n接口降级说明：{exc}",
                "raw": {"source": "deepseek-error", "error": str(exc)},
                "prompt": prompt,
            }

    @classmethod
    def _call_deepseek(cls, prompt):
        url = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"
        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "你是水稻病虫害诊断顾问。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=25) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise AdviceServiceError("DeepSeek 请求失败。") from exc

        try:
            text = raw["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AdviceServiceError("DeepSeek 返回格式异常。") from exc
        return raw, text

    @classmethod
    def _fallback_advice(cls, detections):
        labels = ", ".join(sorted({item["label"] for item in detections}))
        return (
            f"检测到的主要病虫害为：{labels}。\n"
            "建议优先复查田间受害范围，清除明显病残体，保持田间通风透光；"
            "必要时结合当地农技站推荐药剂与防治时期进行处理，并严格遵守安全间隔期。结果仅供参考。"
        )


__all__ = ["AdviceService", "AdviceServiceError", "AdviceRecord", "build_detection_summary"]
