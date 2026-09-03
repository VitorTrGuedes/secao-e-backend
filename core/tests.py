from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Article, Comment, Suggestion

# Create your tests here.
class ArticleAPITest(APITestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title = "Review: Attack on Titan",
            slug = "review-attack-on-titan",
            category = "anime",
            post_type = "review",
            content = "Excelente anime do início ao fim",
            rating = 10
        )

        Comment.objects.create(
            article = self.article,
            author_name = "Eren",
            opinion = "Tatakae!",
            is_approved = True
        )

    def test_listar_artigos(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_detalhar_artigo_por_slug(self):
        response = self.client.get(f'/api/articles/{self.article.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Review: Attack on Titan")



class CommentAPITest(APITestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title = "Filme Batman",
            slug = "filme-batman",
            category = "cinema",
            post_type = "news",
            content = "Novo filme em produção.",
        )

    def test_criar_comentario_valido(self):
        payload = {
            "article": self.article.id,
            "author_name": "Bruce",
            "opinion": "Filme promissor"
        }
        response = self.client.post('/api/comments/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

class SuggestionAPITest(APITestCase):
    def test_criar_sugestao_valida(self):
        payload = {
            "author_name": "OtakuGirl",
            "title_suggested": "Demon Slayer Hashira Arc",
            "category": "anime",
            "reason": "Quero ver sua nota para essa temporada"
        }
        response = self.client.post('/api/suggestions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
