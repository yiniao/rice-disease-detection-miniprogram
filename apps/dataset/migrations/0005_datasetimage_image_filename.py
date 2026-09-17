from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0004_datasetimage_category_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasetimage",
            name="image_filename",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
