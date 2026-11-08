import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import StreamingAvailabilityCache

logger = logging.getLogger(__name__)


class StreamingServiceError(Exception):
    """Raised when the TMDB streaming provider cannot be used."""


class StreamingTitleNotFoundError(StreamingServiceError):
    """Raised when TMDB has no movie matching the requested title."""


def _request_tmdb(path, params):
    api_key = getattr(settings, 'TMDB_API_KEY', '')
    if not api_key:
        raise StreamingServiceError('TMDB_API_KEY não está configurada.')
    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/{path}',
            params={**params, 'api_key': api_key},
            timeout=8,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        logger.exception('Falha ao consultar o TMDB.')
        raise StreamingServiceError(
            'Não foi possível consultar os serviços de streaming.'
        ) from error


def get_streaming_availability(title):
    query = title.strip().lower()
    cache_expiry = timezone.now() - timedelta(
        hours=getattr(settings, 'TMDB_CACHE_TTL_HOURS', 24)
    )
    cached = StreamingAvailabilityCache.objects.filter(
        query=query,
        fetched_at__gte=cache_expiry,
    ).first()
    if cached:
        return cached

    search = _request_tmdb(
        'search/movie',
        {'query': title, 'language': 'pt-BR', 'region': 'BR', 'include_adult': 'false'},
    )
    result = next(iter(search.get('results', [])), None)
    if not result:
        raise StreamingTitleNotFoundError('Filme não encontrado.')

    providers_data = _request_tmdb(
        f"movie/{result['id']}/watch/providers",
        {},
    ).get('results', {}).get('BR', {})
    providers = []
    seen = set()
    for offer_type in ('flatrate', 'free', 'ads', 'rent', 'buy'):
        for provider in providers_data.get(offer_type, []) or []:
            provider_id = provider.get('provider_id')
            if provider_id in seen:
                continue
            seen.add(provider_id)
            providers.append({
                'id': provider_id,
                'name': provider.get('provider_name'),
                'logo_path': provider.get('logo_path'),
                'type': offer_type,
            })

    release_year = (result.get('release_date') or '')[:4]
    cached, _ = StreamingAvailabilityCache.objects.update_or_create(
        query=query,
        defaults={
            'title': result.get('title') or result.get('original_title') or title,
            'year': release_year,
            'tmdb_id': result['id'],
            'providers': providers,
            'fetched_at': timezone.now(),
        },
    )
    return cached
