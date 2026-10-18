from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.core.management import call_command
from rest_framework.test import APITestCase
from rest_framework import status
from .content import extract_article_content
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
        self.assertEqual(response.data[0]['post_type'], 'review')
        self.assertEqual(response.data[0]['comments'][0]['opinion'], 'Tatakae!')

    def test_limpa_html_de_conteudo_antigo_na_resposta(self):
        self.article.content = (
            '<p>Anime &amp; cultura <strong>em destaque</strong></p>'
            '<img alt="capa" src="https://example.com/capa.jpg">'
            '<script>conteudo indesejado</script>'
        )
        self.article.save(update_fields=['content'])

        response = self.client.get(f'/api/articles/{self.article.slug}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Anime & cultura em destaque')

    def test_separa_link_da_fonte_do_conteudo_da_publicacao(self):
        self.article.content = (
            'Resumo da notícia.\n\n(Fonte original: https://example.com/noticia)'
        )
        self.article.save(update_fields=['content'])

        response = self.client.get(f'/api/articles/{self.article.slug}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Resumo da notícia.')
        self.assertEqual(response.data['source_url'], 'https://example.com/noticia')

    def test_detalhar_artigo_por_slug(self):
        response = self.client.get(f'/api/articles/{self.article.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Review: Attack on Titan")
        self.assertEqual(response.data['comments'][0]['opinion'], 'Tatakae!')


class BuscarNoticiasCommandTest(APITestCase):
    @patch(
        'core.management.commands.buscar_noticias.FEEDS',
        [{
            'url': 'https://example.com/feed.xml',
            'category': 'cinema',
        }],
    )
    @patch('core.management.commands.buscar_noticias.urllib.request.urlopen')
    @patch('core.management.commands.buscar_noticias.feedparser.parse')
    def test_importa_todas_as_noticias_do_feed(self, parse_feed, urlopen):
        urlopen.return_value = BytesIO(b'<rss/>')
        parse_feed.return_value = SimpleNamespace(entries=[
            SimpleNamespace(
                title='Notícia Um',
                summary='<p>Resumo &amp; destaque <strong>do feed</strong>.</p>'
                        '<img alt="capa" src="https://example.com/poster.jpg">',
                link='https://example.com/1',
                media_thumbnail=[{'url': 'https://example.com/thumb.jpg'}],
            ),
            SimpleNamespace(title='Notícia Dois', summary='Resumo dois', link='https://example.com/2'),
        ])

        call_command('buscar_noticias')

        self.assertEqual(Article.objects.count(), 2)
        self.assertSetEqual(
            set(Article.objects.values_list('title', flat=True)),
            {'Notícia Um', 'Notícia Dois'},
        )
        article = Article.objects.get(title='Notícia Um')
        self.assertEqual(article.content, 'Resumo & destaque do feed.\n\n(Fonte original: https://example.com/1)')
        self.assertEqual(article.image_url, 'https://example.com/thumb.jpg')

    @patch(
        'core.management.commands.buscar_noticias.FEEDS',
        [{'url': 'https://example.com/feed.xml', 'category': 'cinema'}],
    )
    @patch('core.management.commands.buscar_noticias.urllib.request.urlopen')
    @patch('core.management.commands.buscar_noticias.feedparser.parse')
    def test_importa_resumo_completo_e_atualiza_noticia_automatica_existente(
        self, parse_feed, urlopen
    ):
        urlopen.return_value = BytesIO(b'<rss/>')
        full_summary = 'Palavra ' * 100
        parse_feed.return_value = SimpleNamespace(entries=[
            SimpleNamespace(
                title='Notícia Existente',
                summary=f'<p>{full_summary}</p>',
                link='https://example.com/noticia',
                enclosures=[{
                    'href': '/images/capa.jpg',
                    'type': 'image/jpeg',
                }],
            ),
        ])
        article = Article.objects.create(
            title='Notícia Existente',
            slug='noticia-existente',
            author='Redação Seção E',
            category='cinema',
            post_type='news',
            image_url='https://images.unsplash.com/example.jpg',
            content='Resumo anteriormente truncado...',
        )

        call_command('buscar_noticias')

        article.refresh_from_db()
        self.assertEqual(article.content, f'{full_summary.strip()}\n\n(Fonte original: https://example.com/noticia)')
        self.assertEqual(article.image_url, 'https://example.com/images/capa.jpg')
        self.assertEqual(Article.objects.count(), 1)

    def test_corrige_espacamento_e_entidades_em_html_rss(self):
        text, image_url = extract_article_content(
            'matando<strong>A</strong> Paramount &amp; outras &lt;em&gt;notícias&lt;/em&gt;'
        )

        self.assertEqual(text, 'matando A Paramount & outras notícias')
        self.assertIsNone(image_url)


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
        
