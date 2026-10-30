from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_comment_email_confirmation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='category',
            field=models.CharField(
                choices=[
                    ('cinema', 'Cinema'),
                    ('anime', 'Anime'),
                    ('serie', 'Série'),
                    ('games', 'Games'),
                ],
                max_length=10,
            ),
        ),
    ]
