import feedparser
from django.core.management.base import BaseCommand
from django.utils.text import slugify
import urllib
import ssl
from core.models import Article

# Fontes RSS de notícias públicas
FEEDS = [
    {
        'url': 'https://br.ign.com/feed.xml',
        'category': 'cinema',
        'default_image': 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800'
    },

    {
        'url': 'https://br.ign.com/feed.xml',
        'category': 'serie',
        'default_image': 'https://images.unsplash.com/photo-1522869635100-9f4c5e86aa37?w=800' 
    },

    {
        'url': 'https://www.otakupt.com/feed/',
        'category': 'anime',
        'default_image': 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800'
    }
]

# Palavras-chave para identificar se a matéria é sobre SÈries / STREAMINGS
PALAVRAS_CHAVE_SERIES = [
    'série', 'series', 'temporada', 'episódio', 'episodio', 'season',
    'netflix', 'hbo', 'max', 'prime video', 'disney+', 'apple tv',
    'showrunner', 'sitcom', 'spin-off', 'minissérie', 'minisserie'
]

class Command(BaseCommand):
    help = 'Coleta notícias automáticas de Cinema, Animes e Séries via RSS'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando Varredura de notícias...")
        total_novas = 0

         # Simula um navegador real para não ser bloqueado pelos sites
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

        ssl_context = ssl._create_unverified_context()

        for source in FEEDS:
            try:
                # Faz a requisição simulando o navegador
                req = urllib.request.Request(source['url'], headers=headers)
                with urllib.request.urlopen(req, timeout=12, context =ssl_context) as response:
                    xml_content = response.read()

                feed = feedparser.parse(xml_content)

                # Pega as 6 notícias mais recentes de cada fonte
                for entry in feed.entries[:6]:
                    title = getattr(entry, 'title', '').strip()
                    if not title:
                        continue

                    slug = slugify(title)[:50]
                    if not title:
                         continue

                # Evita duplicatas: se ja cadastrou, pula para a proxima
                if Article.objects.filter(slug=slug).exists():
                    continue

                 # Resumo da matéria
                summary = ''
                if hasattr(entry, 'summary'):
                    summary = entry.summary
                elif hasattr(entry, 'description'):
                    summary = entry.description

                texto_limpo = summary.replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b1>', '')[:400]

                # 🔍 CLASSIFICADOR INTELIGENTE DE CATEGORIA:
                texto_completo = f"{title} {texto_limpo}".lower()

                if source['category'] == 'anime':
                    categoria = 'anime'
                elif any(termo in texto_completo for termo in PALAVRAS_CHAVE_SERIES):
                    categoria = 'serie' # Identificou que é Série autoamticamente
                else:
                    categoria = 'cinema'

                # Tenta capturar a imagem da notícia
                image_url = source['default_image']
                if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url', image_url)
                elif hasattr(entry, 'links'):
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            image_url = link.get('href', image_url)
                            break

                link_original = getattr(entry, 'link', '#')

                # Salva no banco de dados
                Article.objects.create(
                    title=title,
                    slug=slug,
                    author="Redação Seção E",
                    category=categoria,
                    post_type="news",
                    image_url=image_url,
                    content=f"{texto_limpo}...\n\n(Fonte original: {link_original})",
                    rating=None
                )
                total_novas += 1
                self.stdout.write(f"[{categoria.upper()}] {title}")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao ler o feed {source['url']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nFinalizado! {total_novas} notícias adicionadas com sucesso!"))


        