from django.db import models

# Categotias de escolha

CATEGORY_CHOICES = (('cinema', 'Cinema'), 
                    ('anime', 'Anime'),
                    ('serie', 'Série')
)

class Article(models.Model):
    TYPE_CHOICES = (('news', 'Notícia'), ('review', 'Crítica'))
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
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
    opinion = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Suggestion(models.Model):
    author_name = models.CharField(max_length=100)
    title_suggested = models.CharField(max_length=200)
    category = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)