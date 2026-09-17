import base64
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.dataset.models import DatasetImage
from apps.diagnosis.models import DetectionRecord


User = get_user_model()


def build_test_image(name="sample.jpg", color="green"):
    buffer = BytesIO()
    image = Image.new("RGB", (240, 180), color=color)
    image.save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def build_test_image_base64(color="green"):
    buffer = BytesIO()
    image = Image.new("RGB", (240, 180), color=color)
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@override_settings(DEEPSEEK_API_KEY="", MEDIA_ROOT="test_media")
class WebPortalTests(TestCase):
    def test_root_page_is_user_web_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "网页端")

    def test_web_dashboard_requires_login(self):
        response = self.client.get("/web/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_logged_in_user_can_open_web_dashboard(self):
        user = User.objects.create_user(username="webuser", password="secret123")
        self.client.login(username="webuser", password="secret123")
        response = self.client.get("/web/")
        self.assertEqual(response.status_code, 200)

    def test_logged_in_user_can_open_statistics_page(self):
        user = User.objects.create_user(username="statsuser", password="secret123")
        self.client.login(username="statsuser", password="secret123")
        response = self.client.get("/web/statistics/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "检测记录数据统计")

    def test_logged_in_user_can_delete_dataset_item(self):
        user = User.objects.create_user(username="webuser2", password="secret123")
        detection = DetectionRecord.objects.create(user=user, original_image=build_test_image_base64())
        item = DatasetImage.objects.create(user=user, source_detection=detection, image=build_test_image_base64())

        self.client.login(username="webuser2", password="secret123")
        response = self.client.post(f"/web/dataset/{item.id}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/web/dataset/")
        self.assertFalse(DatasetImage.objects.filter(pk=item.id).exists())
