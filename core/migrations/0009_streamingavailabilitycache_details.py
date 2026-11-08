from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_streamingavailabilitycache'),
    ]

    operations = [
        migrations.AddField(
            model_name='streamingavailabilitycache',
            name='media_type',
            field=models.CharField(default='movie', max_length=10),
        ),
        migrations.AddField(
            model_name='streamingavailabilitycache',
            name='overview',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='streamingavailabilitycache',
            name='poster_path',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='streamingavailabilitycache',
            name='release_date',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
