from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_analysis", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="advicerecord",
            name="source",
            field=models.CharField(
                choices=[("deepseek", "DeepSeek"), ("local-fallback", "本地兜底")],
                default="local-fallback",
                max_length=32,
            ),
        ),
    ]
