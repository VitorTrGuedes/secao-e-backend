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


def _providers_for(media_type, tmdb_id):
    providers_data = _request_tmdb(
        f'{media_type}/{tmdb_id}/watch/providers',
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
    return providers


def _title_from_result(result, providers):
    media_type = result.get('media_type', 'movie')
    release_date = result.get('release_date') or result.get('first_air_date') or ''
    return {
        'id': result['id'],
        'tmdb_id': result['id'],
        'media_type': media_type,
        'title': result.get('title') or result.get('name') or result.get('original_title') or result.get('original_name'),
        'year': release_date[:4],
        'release_date': release_date,
        'overview': result.get('overview') or '',
        'poster_path': result.get('poster_path') or '',
        'providers': providers,
    }


def _title_from_cache(cached):
    return {
        'id': cached.tmdb_id,
        'tmdb_id': cached.tmdb_id,
        'media_type': cached.media_type,
        'title': cached.title,
        'year': cached.year,
        'release_date': cached.release_date,
        'overview': cached.overview,
        'poster_path': cached.poster_path,
        'providers': cached.providers,
    }


def get_streaming_titles(title=''):
    params = {
        'language': 'pt-BR',
        'region': 'BR',
        'include_adult': 'false',
    }
    if title:
        results = _search_titles(title, params)
    else:
        movies = _request_tmdb(
            'discover/movie',
            {**params, 'sort_by': 'popularity.desc', 'with_watch_region': 'BR', 'page': 1},
        ).get('results', [])
        series = _request_tmdb(
            'discover/tv',
            {**params, 'sort_by': 'popularity.desc', 'with_watch_region': 'BR', 'page': 1},
        ).get('results', [])
        results = [
            {**item, 'media_type': 'movie'} for item in movies[:5]
        ] + [
            {**item, 'media_type': 'tv'} for item in series[:5]
        ]

    titles = [
        _title_from_result(result, _providers_for(result.get('media_type', 'movie'), result['id']))
        for result in results
    ]
    return titles


def _search_titles(title, params):
    results = _request_tmdb(
        'search/multi',
        {**params, 'query': title},
    ).get('results', [])
    results = [
        item for item in results
        if item.get('media_type') in ('movie', 'tv')
    ]
    if not results:
        results = _request_tmdb(
            'search/multi',
            {**params, 'language': 'en-US', 'query': title},
        ).get('results', [])
        results = [
            item for item in results
            if item.get('media_type') in ('movie', 'tv')
        ]
    return results[:20]


def get_title_details(title):
    params = {
        'language': 'pt-BR',
        'region': 'BR',
        'include_adult': 'false',
    }
    results = _search_titles(title, params)
    result = next(iter(results), None)
    if not result:
        raise StreamingTitleNotFoundError('Título não encontrado.')

    media_type = result.get('media_type', 'movie')
    details = _request_tmdb(
        f"{media_type}/{result['id']}",
        {
            'language': 'pt-BR',
            'append_to_response': 'credits',
        },
    )
    credits = details.get('credits', {})
    crew = credits.get('crew', [])
    directors = [
        person.get('name') for person in crew
        if person.get('job') == 'Director' and person.get('name')
    ]
    writers = [
        person.get('name') for person in crew
        if person.get('job') in {'Writer', 'Screenplay', 'Story'} and person.get('name')
    ]
    cast = [
        person.get('name') for person in credits.get('cast', [])
        if person.get('name')
    ][:8]
    release_date = details.get('release_date') or details.get('first_air_date') or ''
    runtime = details.get('runtime')
    if runtime is None:
        runtimes = details.get('episode_run_time') or []
        runtime = runtimes[0] if runtimes else None

    return {
        'id': details.get('id'),
        'title': details.get('title') or details.get('name') or title,
        'original_title': details.get('original_title') or details.get('original_name') or '',
        'media_type': media_type,
        'year': release_date[:4],
        'release_date': release_date,
        'runtime': runtime,
        'genres': [genre.get('name') for genre in details.get('genres', []) if genre.get('name')],
        'popularity': details.get('popularity'),
        'vote_average': details.get('vote_average'),
        'vote_count': details.get('vote_count'),
        'director': directors[0] if directors else '',
        'writers': list(dict.fromkeys(writers))[:4],
        'cast': cast,
        'tmdb_url': f"https://www.themoviedb.org/{media_type}/{details.get('id')}",
    }


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

    providers = _providers_for('movie', result['id'])
    details = _title_from_result(result, providers)
    cached, _ = StreamingAvailabilityCache.objects.update_or_create(
        query=query,
        defaults={
            'title': details['title'],
            'year': details['year'],
            'tmdb_id': result['id'],
            'media_type': 'movie',
            'overview': details['overview'],
            'poster_path': details['poster_path'],
            'release_date': details['release_date'],
            'providers': providers,
            'fetched_at': timezone.now(),
        },
    )
    return cached
