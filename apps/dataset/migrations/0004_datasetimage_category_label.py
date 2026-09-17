from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0003_alter_datasetimage_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasetimage",
            name="category_label",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
