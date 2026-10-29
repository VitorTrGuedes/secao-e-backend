from io import BytesIO
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
from datetime import timedelta
import urllib.error
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.throttling import SimpleRateThrottle
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
            email = "eren@example.com",
            opinion = "Tatakae!",
            is_approved = True
        )

    def test_listar_artigos(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['post_type'], 'review')
        self.assertEqual(response.data[0]['comments'][0]['opinion'], 'Tatakae!')

    def test_listagem_busca_comentarios_em_uma_consulta(self):
        for index in range(3):
            article = Article.objects.create(
                title=f'Análise {index}',
                slug=f'analise-{index}',
                category='cinema',
                post_type='review',
                content='Conteúdo da análise.',
            )
            Comment.objects.create(
                article=article,
                author_name='Leitor',
                email='leitor@example.com',
                opinion='Comentário aprovado.',
                is_approved=True,
            )
            Comment.objects.create(
                article=article,
                author_name='Moderador',
                email='moderador@example.com',
                opinion='Comentário pendente.',
                is_approved=False,
            )

        with self.assertNumQueries(2):
            response = self.client.get('/api/articles/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertTrue(all(len(article['comments']) == 1 for article in response.data))

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

    def test_entrega_html_formatado_sem_elementos_ou_links_perigosos(self):
        self.article.content = (
            '<p>Texto <strong>com destaque</strong></p>'
            '<script>alert("x")</script>'
            '<a href="javascript:alert(1)">link inseguro</a>'
        )
        self.article.save(update_fields=['content'])

        response = self.client.get(f'/api/articles/{self.article.slug}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['content_html'],
            '<p>Texto <strong>com destaque</strong></p><a>link inseguro</a>',
        )

    def test_promove_imagem_principal_e_remove_repeticao_do_corpo(self):
        self.article.image_url = 'https://example.com/capa-generica.jpg'
        self.article.content = (
            '<figure><img src="/images/capa.jpg">'
            '<figcaption>Imagem promocional</figcaption></figure>'
            '<p>Texto integral da notícia.</p>'
            '<img src="https://example.com/images/outra.jpg">'
            '\n\n(Fonte original: https://example.com/noticia)'
        )
        self.article.save(update_fields=['image_url', 'content'])

        response = self.client.get(f'/api/articles/{self.article.slug}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['image_url'],
            'https://example.com/images/capa.jpg',
        )
        self.assertEqual(
            response.data['content_html'],
            '<figure><figcaption>Imagem promocional</figcaption></figure>'
            '<p>Texto integral da notícia.</p>'
            '<img src="https://example.com/images/outra.jpg" alt="" loading="lazy">',
        )

    def test_detalhar_artigo_por_slug(self):
        response = self.client.get(f'/api/articles/{self.article.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Review: Attack on Titan")
        self.assertEqual(response.data['comments'][0]['opinion'], 'Tatakae!')


class BuscarNoticiasCommandTest(APITestCase):
    @patch(
        'core.management.commands.buscar_noticias.FEEDS',
        [],
    )
    def test_remove_noticias_automaticas_com_mais_de_uma_semana(self):
        antiga = Article.objects.create(
            title='Notícia automática antiga',
            slug='noticia-automatica-antiga',
            author='Redação Seção E',
            category='cinema',
            post_type='news',
            content='Conteúdo antigo',
        )
        antiga.created_at = timezone.now() - timedelta(days=8)
        antiga.save(update_fields=['created_at'])

        manual = Article.objects.create(
            title='Notícia manual antiga',
            slug='noticia-manual-antiga',
            author='Outro autor',
            category='cinema',
            post_type='news',
            content='Conteúdo manual',
        )
        manual.created_at = timezone.now() - timedelta(days=8)
        manual.save(update_fields=['created_at'])

        recente = Article.objects.create(
            title='Notícia automática recente',
            slug='noticia-automatica-recente',
            author='Redação Seção E',
            category='cinema',
            post_type='news',
            content='Conteúdo recente',
        )

        call_command('buscar_noticias')

        self.assertFalse(Article.objects.filter(pk=antiga.pk).exists())
        self.assertTrue(Article.objects.filter(pk=manual.pk).exists())
        self.assertTrue(Article.objects.filter(pk=recente.pk).exists())

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
                content=[{
                    'type': 'text/html',
                    'value': (
                        f'<p>{full_summary.strip()}</p>'
                        '<img src="/images/capa-principal.jpg" onerror="alert(1)">'
                    ),
                }],
                link='https://example.com/noticia',
                enclosures=[{
                    'href': '/images/capa-miniatura.jpg',
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
        self.assertEqual(
            article.content,
            f'<p>{full_summary.strip()}</p>'
            '<img src="https://example.com/images/capa-principal.jpg" alt="" loading="lazy">'
            '\n\n(Fonte original: https://example.com/noticia)',
        )
        self.assertEqual(article.image_url, 'https://example.com/images/capa-principal.jpg')
        self.assertEqual(Article.objects.count(), 1)

    def test_corrige_espacamento_e_entidades_em_html_rss(self):
        text, image_url = extract_article_content(
            'matando<strong>A</strong> Paramount &amp; outras &lt;em&gt;notícias&lt;/em&gt;'
        )

        self.assertEqual(text, 'matando A Paramount & outras notícias')
        self.assertIsNone(image_url)

    @patch(
        'core.management.commands.buscar_noticias.FEEDS',
        [
            {'url': 'https://unavailable.example/feed.xml', 'category': 'anime'},
            {'url': 'https://available.example/feed.xml', 'category': 'cinema'},
        ],
    )
    @patch('core.management.commands.buscar_noticias.urllib.request.urlopen')
    @patch('core.management.commands.buscar_noticias.feedparser.parse')
    def test_importa_feeds_acessiveis_quando_outro_feed_falha(
        self, parse_feed, urlopen
    ):
        urlopen.side_effect = [
            urllib.error.URLError('connection refused'),
            BytesIO(b'<rss/>'),
        ]
        parse_feed.return_value = SimpleNamespace(entries=[
            SimpleNamespace(
                title='Notícia do feed acessível',
                summary='Resumo disponível',
                link='https://available.example/noticia',
            ),
        ])
        error_output = StringIO()

        call_command('buscar_noticias', stderr=error_output)

        self.assertTrue(
            Article.objects.filter(title='Notícia do feed acessível').exists()
        )
        self.assertIn(
            'Os feeds acessíveis foram importados.',
            error_output.getvalue(),
        )

    @patch(
        'core.management.commands.buscar_noticias.FEEDS',
        [{'url': 'https://unavailable.example/feed.xml', 'category': 'anime'}],
    )
    @patch('core.management.commands.buscar_noticias.urllib.request.urlopen')
    def test_falha_explicitamente_quando_todos_os_feeds_estao_indisponiveis(
        self, urlopen
    ):
        urlopen.side_effect = urllib.error.URLError('connection refused')

        with self.assertRaisesMessage(
            CommandError, 'Falha ao consultar 1 feed(s) RSS'
        ):
            call_command('buscar_noticias')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='https://secao-e.example',
)
class CommentAPITest(APITestCase):
    def setUp(self):
        SimpleRateThrottle.cache.clear()
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
            "email": "bruce@example.com",
            "opinion": "Filme promissor",
        }
        response = self.client.post('/api/comments/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('email', response.data)
        self.assertFalse(Comment.objects.get().is_approved)
        self.assertEqual(len(mail.outbox), 1)

    def test_comentario_so_aparece_apos_confirmar_email(self):
        response = self.client.post('/api/comments/', {
            'article': self.article.id,
            'author_name': 'Bruce',
            'email': 'bruce@example.com',
            'opinion': 'Filme promissor',
        })
        comment = Comment.objects.get()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(comment.is_approved)

        pending_article = self.client.get(f'/api/articles/{self.article.slug}/')
        self.assertEqual(pending_article.data['comments'], [])

        confirmation_url = mail.outbox[0].body.splitlines()[3]
        token = parse_qs(urlsplit(confirmation_url).query)['token'][0]
        confirmation = self.client.post('/api/comments/confirm/', {'token': token})

        self.assertEqual(confirmation.status_code, status.HTTP_200_OK)
        self.assertEqual(confirmation.data['article_slug'], self.article.slug)
        comment.refresh_from_db()
        self.assertTrue(comment.is_approved)
        self.assertEqual(comment.email_confirmation_token, '')

        article_response = self.client.get(f'/api/articles/{self.article.slug}/')
        self.assertEqual(len(article_response.data['comments']), 1)
        self.assertNotIn('email', article_response.data['comments'][0])

        reused_token = self.client.post('/api/comments/confirm/', {'token': token})
        self.assertEqual(reused_token.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejeita_email_invalido_sem_criar_comentario(self):
        response = self.client.post('/api/comments/', {
            'article': self.article.id,
            'author_name': 'Bruce',
            'email': 'endereco-invalido',
            'opinion': 'Filme promissor',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_link_de_confirmacao_expirado_nao_publica_comentario(self):
        self.client.post('/api/comments/', {
            'article': self.article.id,
            'author_name': 'Bruce',
            'email': 'bruce@example.com',
            'opinion': 'Filme promissor',
        })
        comment = Comment.objects.get()
        confirmation_url = mail.outbox[0].body.splitlines()[3]
        token = parse_qs(urlsplit(confirmation_url).query)['token'][0]
        comment.email_confirmation_sent_at = timezone.now() - timedelta(hours=25)
        comment.save(update_fields=['email_confirmation_sent_at'])

        response = self.client.post('/api/comments/confirm/', {'token': token})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        comment.refresh_from_db()
        self.assertFalse(comment.is_approved)

    @patch('core.views.send_mail', side_effect=RuntimeError('Email provider unavailable'))
    def test_falha_de_envio_nao_salva_comentario_pendente(self, send_mail_mock):
        with self.assertLogs('core.views', level='ERROR'):
            response = self.client.post('/api/comments/', {
                'article': self.article.id,
                'author_name': 'Bruce',
                'email': 'bruce@example.com',
                'opinion': 'Filme promissor',
            })

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(Comment.objects.count(), 0)
        send_mail_mock.assert_called_once()

class SuggestionAPITest(APITestCase):
    def setUp(self):
        SimpleRateThrottle.cache.clear()

    def test_criar_sugestao_valida(self):
        payload = {
            "author_name": "OtakuGirl",
            "title_suggested": "Demon Slayer Hashira Arc",
            "category": "anime",
            "reason": "Quero ver sua nota para essa temporada"
        }
        response = self.client.post('/api/suggestions/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
