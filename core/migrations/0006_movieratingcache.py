from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_article_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='MovieRatingCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=200, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('year', models.CharField(blank=True, max_length=20)),
                ('imdb_id', models.CharField(blank=True, max_length=20)),
                ('imdb_rating', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('imdb_votes', models.PositiveIntegerField(blank=True, null=True)),
                ('rotten_tomatoes_rating', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('fetched_at', models.DateTimeField()),
            ],
        ),
    ]
