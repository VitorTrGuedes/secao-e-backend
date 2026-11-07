from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_movieratingcache'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='ratings_title',
            field=models.CharField(
                blank=True,
                help_text='Título original usado para buscar notas no IMDb e Rotten Tomatoes.',
                max_length=200,
            ),
        ),
    ]
