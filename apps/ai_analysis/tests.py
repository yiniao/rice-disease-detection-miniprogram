from django.test import TestCase, override_settings

from .models import AdviceRecord
from .services import AdviceService


@override_settings(DEEPSEEK_API_KEY="")
class AdviceServiceTests(TestCase):
    def test_fallback_advice_contains_reference_notice(self):
        payload = AdviceService.generate(
            [{"label": "leaf_blast", "confidence": 0.81, "xmin": 1, "ymin": 1, "xmax": 2, "ymax": 2}]
        )
        self.assertEqual(payload["status"], AdviceRecord.Status.FALLBACK)
        self.assertEqual(payload["source"], AdviceRecord.Source.LOCAL_FALLBACK)
        self.assertIn("仅供参考", payload["text"])
