from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("diagnosis", "0002_alter_detectionrecord_original_image_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="detectionrecord",
            name="original_filename",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
