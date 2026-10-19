import feedparser
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit
from core.content import extract_article_content, sanitize_article_html
from core.models import Article

# Fontes RSS de notícias públicas
FEEDS = [
    {
        'url': 'https://br.ign.com/feed.xml',
        'category': 'cinema',
    },

    {
        'url': 'https://br.ign.com/feed.xml',
        'category': 'serie',
    },

    {
        'url': 'https://www.otakupt.com/feed/',
        'category': 'anime',
    }
]

# Palavras-chave para identificar se a matéria é sobre SÈries / STREAMINGS
PALAVRAS_CHAVE_SERIES = [
    'série', 'series', 'temporada', 'episódio', 'episodio', 'season',
    'netflix', 'hbo', 'max', 'prime video', 'disney+', 'apple tv',
    'showrunner', 'sitcom', 'spin-off', 'minissérie', 'minisserie'
]


def _entry_value(entry, key, default=None):
    if hasattr(entry, 'get'):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _media_image_url(media, base_url):
    media_url = _entry_value(media, 'url') or _entry_value(media, 'href')
    if not media_url:
        return None

    medium = str(_entry_value(media, 'medium', '')).lower()
    media_type = str(_entry_value(media, 'type', '')).lower()
    if medium and medium != 'image':
        return None
    if media_type and media_type != 'image' and not media_type.startswith('image/'):
        return None

    resolved_url = urljoin(base_url, str(media_url))
    if urlsplit(resolved_url).scheme not in {'http', 'https'}:
        return None
    return resolved_url


def _find_entry_image(entry, summary_image, base_url):
    candidate_groups = (
        _entry_value(entry, 'media_content', []),
        _entry_value(entry, 'media_thumbnail', []),
        _entry_value(entry, 'enclosures', []),
    )
    for candidates in candidate_groups:
        for candidate in candidates or []:
            image_url = _media_image_url(candidate, base_url)
            if image_url:
                return image_url

    for link in _entry_value(entry, 'links', []) or []:
        link_type = str(_entry_value(link, 'type', '')).lower()
        if 'image' not in link_type:
            continue
        image_url = _media_image_url(link, base_url)
        if image_url:
            return image_url

    for image_url in (summary_image,):
        if image_url:
            resolved_url = urljoin(base_url, image_url)
            if urlsplit(resolved_url).scheme in {'http', 'https'}:
                return resolved_url

    for content in _entry_value(entry, 'content', []) or []:
        content_value = _entry_value(content, 'value', '')
        _, content_image = extract_article_content(content_value)
        if content_image:
            resolved_url = urljoin(base_url, content_image)
            if urlsplit(resolved_url).scheme in {'http', 'https'}:
                return resolved_url

    return None


def _entry_full_content(entry):
    for content in _entry_value(entry, 'content', []) or []:
        content_value = _entry_value(content, 'value', '')
        if content_value:
            return content_value
    return ''


class Command(BaseCommand):
    help = 'Coleta notícias automáticas de Cinema, Animes e Séries via RSS'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando Varredura de notícias...")
        total_novas = 0
        total_atualizadas = 0

        # Simula um navegador real para não ser bloqueado pelos sites
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

        falhas_feed = []

        for source in FEEDS:
            try:
                req = urllib.request.Request(source['url'], headers=headers)
                with urllib.request.urlopen(req, timeout=12) as response:
                    xml_content = response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                falhas_feed.append(source['url'])
                self.stderr.write(self.style.WARNING(
                    f"Erro ao ler o feed {source['url']}: {exc}"
                ))
                continue

            feed = feedparser.parse(xml_content)

            for entry in feed.entries[:6]:
                title = getattr(entry, 'title', '').strip()
                if not title:
                    continue

                slug = slugify(title)[:50]
                if not slug:
                    continue
                existing_article = Article.objects.filter(slug=slug).first()
                if existing_article and (
                    existing_article.author != "Redação Seção E"
                    or existing_article.post_type != "news"
                    or existing_article.title != title
                ):
                    continue

                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                full_content = _entry_full_content(entry)
                article_source = full_content or summary
                if full_content:
                    texto_limpo, content_image = extract_article_content(full_content)
                    summary_text, summary_image = extract_article_content(summary)
                    texto_limpo = texto_limpo or summary_text
                    summary_image = summary_image or content_image
                else:
                    texto_limpo, summary_image = extract_article_content(summary)
                texto_completo = f"{title} {texto_limpo}".lower()

                if source['category'] == 'anime':
                    categoria = 'anime'
                elif any(termo in texto_completo for termo in PALAVRAS_CHAVE_SERIES):
                    categoria = 'serie'
                else:
                    categoria = 'cinema'

                link_original = getattr(entry, 'link', '')
                image_url = _find_entry_image(entry, summary_image, link_original or source['url'])
                article_content = (
                    sanitize_article_html(article_source, base_url=link_original or source['url'])
                    if full_content else texto_limpo
                )
                if link_original:
                    article_content = f"{article_content}\n\n(Fonte original: {link_original})"

                if existing_article:
                    existing_article.category = categoria
                    existing_article.image_url = image_url
                    existing_article.content = article_content
                    existing_article.save(update_fields=['category', 'image_url', 'content'])
                    total_atualizadas += 1
                    self.stdout.write(f"[ATUALIZADA: {categoria.upper()}] {title}")
                else:
                    Article.objects.create(
                        title=title,
                        slug=slug,
                        author="Redação Seção E",
                        category=categoria,
                        post_type="news",
                        image_url=image_url,
                        content=article_content,
                        rating=None
                    )
                    total_novas += 1
                    self.stdout.write(f"[{categoria.upper()}] {title}")

        self.stdout.write(self.style.SUCCESS(
            f"\nFinalizado! {total_novas} notícias adicionadas e {total_atualizadas} atualizadas."
        ))
        if falhas_feed:
            raise CommandError(f"Falha ao consultar {len(falhas_feed)} feed(s) RSS.")