import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import MovieRatingCache

logger = logging.getLogger(__name__)


class RatingsServiceError(Exception):
    """Raised when the external ratings provider cannot be used."""


class RatingsTitleNotFoundError(RatingsServiceError):
    """Raised when the provider has no result for the requested title."""


def _decimal_rating(value):
    if not value or value == 'N/A':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer_rating(value):
    if not value or value == 'N/A':
        return None
    try:
        return int(value.rstrip('%'))
    except (AttributeError, TypeError, ValueError):
        return None


def _integer_votes(value):
    if not value or value == 'N/A':
        return None
    try:
        return int(value.replace(',', ''))
    except (AttributeError, TypeError, ValueError):
        return None


def _find_rating(ratings, source):
    return next(
        (rating.get('Value') for rating in ratings if rating.get('Source') == source),
        None,
    )


def get_movie_ratings(title):
    query = title.strip().lower()
    cache_expiry = timezone.now() - timedelta(
        hours=getattr(settings, 'OMDB_CACHE_TTL_HOURS', 24)
    )
    cached = MovieRatingCache.objects.filter(
        query=query,
        fetched_at__gte=cache_expiry,
    ).first()
    if cached:
        return cached

    api_key = getattr(settings, 'OMDB_API_KEY', '')
    if not api_key:
        raise RatingsServiceError('OMDB_API_KEY não está configurada.')

    try:
        response = requests.get(
            'https://www.omdbapi.com/',
            params={'t': title, 'apikey': api_key, 'r': 'json'},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.exception('Falha ao consultar a OMDb para o título informado.')
        raise RatingsServiceError('Não foi possível consultar o serviço de avaliações.') from error

    if data.get('Response') != 'True':
        raise RatingsTitleNotFoundError(data.get('Error', 'Título não encontrado.'))

    rating, _ = MovieRatingCache.objects.update_or_create(
        query=query,
        defaults={
            'title': data.get('Title', title),
            'year': data.get('Year', ''),
            'imdb_id': data.get('imdbID', ''),
            'imdb_rating': _decimal_rating(data.get('imdbRating')),
            'imdb_votes': _integer_votes(data.get('imdbVotes')),
            'rotten_tomatoes_rating': _integer_rating(
                _find_rating(data.get('Ratings', []), 'Rotten Tomatoes')
            ),
            'fetched_at': timezone.now(),
        },
    )
    return rating
