from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_article_ratings_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='StreamingAvailabilityCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=200, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('year', models.CharField(blank=True, max_length=4)),
                ('tmdb_id', models.PositiveIntegerField()),
                ('providers', models.JSONField(default=list)),
                ('fetched_at', models.DateTimeField()),
            ],
        ),
    ]
