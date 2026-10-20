from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_article_author'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='email',
            field=models.EmailField(default='', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='comment',
            name='email_confirmation_token',
            field=models.CharField(blank=True, default='', editable=False, max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='comment',
            name='email_confirmation_sent_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
    ]
