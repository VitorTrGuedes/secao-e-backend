from django.db import models

# Categotias de escolha

CATEGORY_CHOICES = (('cinema', 'Cinema'), 
                    ('anime', 'Anime'),
                    ('serie', 'Série'),
                    ('games', 'Games')
)

class Article(models.Model):
    TYPE_CHOICES = (('news', 'Notícia'), ('review', 'Crítica'))
    title = models.CharField(max_length=200)
    ratings_title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Título original usado para buscar notas no IMDb e Rotten Tomatoes.',
    )
    slug = models.SlugField(unique=True)
    author = models.CharField(max_length=100, default='Kallavan', verbose_name="Autor")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    post_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='news')
    image_url = models.URLField(blank=True, null=True)
    content = models.TextField()
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"[{self.post_type.upper()}] {self.title}"

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    author_name = models.CharField(max_length=100)
    email = models.EmailField()
    opinion = models.TextField()
    is_approved = models.BooleanField(default=False)
    email_confirmation_token = models.CharField(max_length=64, blank=True, editable=False)
    email_confirmation_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    delete_token_hash = models.CharField(max_length=64, blank=True, editable=False)
    delete_token_expires_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Suggestion(models.Model):
    author_name = models.CharField(max_length=100)
    title_suggested = models.CharField(max_length=200)
    category = models.TextField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class MovieRatingCache(models.Model):
    query = models.CharField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    year = models.CharField(max_length=20, blank=True)
    imdb_id = models.CharField(max_length=20, blank=True)
    imdb_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    imdb_votes = models.PositiveIntegerField(null=True, blank=True)
    rotten_tomatoes_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    fetched_at = models.DateTimeField()

    def __str__(self):
        return self.title


class StreamingAvailabilityCache(models.Model):
    query = models.CharField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    year = models.CharField(max_length=4, blank=True)
    tmdb_id = models.PositiveIntegerField()
    media_type = models.CharField(max_length=10, default='movie')
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    release_date = models.CharField(max_length=20, blank=True)
    providers = models.JSONField(default=list)
    fetched_at = models.DateTimeField()

    def __str__(self):
        return self.title