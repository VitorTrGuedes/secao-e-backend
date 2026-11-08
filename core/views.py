import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Prefetch, Q
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from .models import Article, Comment, Suggestion
from .ratings import RatingsServiceError, RatingsTitleNotFoundError, get_movie_ratings
from .streaming import (
    StreamingServiceError,
    StreamingTitleNotFoundError,
    get_streaming_titles,
)
from .serializers import (
    ArticleSerializer,
    CommentConfirmationSerializer,
    CommentDeletionSerializer,
    CommentSerializer,
    SuggestionSerializer,
)

logger = logging.getLogger(__name__)


class EmailDeliveryUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Não foi possível enviar o e-mail de confirmação. Tente novamente mais tarde.'


class SuggestionDeliveryUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Não foi possível encaminhar a sugestão. Tente novamente mais tarde.'


class PostThrottle(AnonRateThrottle):
    rate = '5/minute'


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        limite_retencao = timezone.now() - timedelta(days=7)
        return Article.objects.exclude(
            author='Redação Seção E',
            post_type='news',
            created_at__lt=limite_retencao,
        ).filter(
            Q(post_type='review') | Q(category__in=['cinema', 'anime', 'serie'])
        ).prefetch_related(
            Prefetch(
                'comments',
                queryset=Comment.objects.filter(is_approved=True),
                to_attr='approved_comments',
            )
        ).order_by('-created_at')


class MovieRatingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        title = request.query_params.get('title', '').strip()
        if not title:
            return Response(
                {'detail': 'Informe o título do filme no parâmetro title.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(title) > 200:
            return Response(
                {'detail': 'O título deve ter no máximo 200 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating = get_movie_ratings(title)
        except RatingsTitleNotFoundError as error:
            return Response({'detail': str(error)}, status=status.HTTP_404_NOT_FOUND)
        except RatingsServiceError as error:
            return Response({'detail': str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            'title': rating.title,
            'year': rating.year,
            'imdb_id': rating.imdb_id or None,
            'imdb_rating': float(rating.imdb_rating) if rating.imdb_rating is not None else None,
            'imdb_votes': rating.imdb_votes,
            'rotten_tomatoes_rating': rating.rotten_tomatoes_rating,
            'fetched_at': rating.fetched_at,
        })


class StreamingAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        title = request.query_params.get('title', '').strip()
        if not title:
            try:
                return Response({'results': get_streaming_titles()})
            except StreamingServiceError as error:
                return Response({'detail': str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if len(title) > 200:
            return Response(
                {'detail': 'O título deve ter no máximo 200 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            titles = get_streaming_titles(title)
        except StreamingTitleNotFoundError as error:
            return Response({'detail': str(error)}, status=status.HTTP_404_NOT_FOUND)
        except StreamingServiceError as error:
            return Response({'detail': str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not titles:
            return Response({'results': []})

        result = titles[0]
        return Response({**result, 'results': titles})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    throttle_classes = [PostThrottle]
    http_method_names = ['post']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(is_approved=False)

        token = secrets.token_urlsafe(32)
        comment.email_confirmation_token = hashlib.sha256(token.encode()).hexdigest()
        comment.email_confirmation_sent_at = timezone.now()
        deletion_token = secrets.token_urlsafe(32)
        comment.delete_token_hash = hashlib.sha256(deletion_token.encode()).hexdigest()
        comment.delete_token_expires_at = timezone.now() + timedelta(days=7)
        comment.save(update_fields=[
            'email_confirmation_token',
            'email_confirmation_sent_at',
            'delete_token_hash',
            'delete_token_expires_at',
        ])

        confirmation_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/confirmar-comentario?"
            f"{urlencode({'token': token})}"
        )
        deletion_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/excluir-comentario?"
            f"{urlencode({'token': deletion_token})}"
        )
        message = (
            f"Olá, {comment.author_name}!\n\n"
            "Para confirmar seu e-mail e publicar seu comentário, acesse:\n"
            f"{confirmation_url}\n\n"
            "Para excluir este comentário, acesse:\n"
            f"{deletion_url}\n\n"
            "O link de confirmação expira em 24 horas e o link de exclusão em 7 dias. "
            "Se você não enviou este comentário, ignore esta mensagem."
        )

        try:
            sent_count = send_mail(
                subject='Confirme seu e-mail para publicar seu comentário',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[comment.email],
                fail_silently=False,
            )
        except Exception as error:
            logger.exception('Falha ao enviar confirmação de e-mail do comentário.')
            raise EmailDeliveryUnavailable() from error

        if sent_count != 1:
            logger.error('O serviço de e-mail não aceitou a confirmação do comentário.')
            raise EmailDeliveryUnavailable()

        return Response(
            {'detail': 'Enviamos um link de confirmação para o e-mail informado.'},
            status=status.HTTP_201_CREATED,
        )


class DeleteCommentView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def delete(self, request):
        serializer = CommentDeletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_hash = hashlib.sha256(
            serializer.validated_data['token'].encode()
        ).hexdigest()
        comment = Comment.objects.select_for_update().filter(
            delete_token_hash=token_hash,
            delete_token_expires_at__gt=timezone.now(),
        ).first()
        if comment is None:
            return Response(
                {'detail': 'Token inválido ou expirado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        comment.delete_token_hash = ''
        comment.delete_token_expires_at = None
        comment.save(update_fields=['delete_token_hash', 'delete_token_expires_at'])
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfirmCommentEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PostThrottle]

    def post(self, request):
        serializer = CommentConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_hash = hashlib.sha256(serializer.validated_data['token'].encode()).hexdigest()

        with transaction.atomic():
            comment = (
                Comment.objects.select_for_update()
                .select_related('article')
                .filter(email_confirmation_token=token_hash)
                .first()
            )
            if comment is None:
                return Response(
                    {'detail': 'O link de confirmação é inválido, expirou ou já foi usado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token_expired = (
                comment.email_confirmation_sent_at is None
                or comment.email_confirmation_sent_at < timezone.now() - timedelta(hours=24)
            )
            if token_expired:
                comment.email_confirmation_token = ''
                comment.email_confirmation_sent_at = None
                comment.save(update_fields=['email_confirmation_token', 'email_confirmation_sent_at'])
                return Response(
                    {'detail': 'O link de confirmação é inválido, expirou ou já foi usado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            comment.is_approved = True
            comment.email_confirmation_token = ''
            comment.email_confirmation_sent_at = None
            comment.save(
                update_fields=[
                    'is_approved',
                    'email_confirmation_token',
                    'email_confirmation_sent_at',
                ]
            )

        return Response({
            'detail': 'E-mail confirmado. Seu comentário já está publicado.',
            'article_slug': comment.article.slug,
        })


class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all()
    serializer_class = SuggestionSerializer
    throttle_classes = [PostThrottle]
    http_method_names = ['post']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = serializer.save()
        message = (
            f'Nova sugestão de crítica recebida pelo site Seção E.\n\n'
            f'Nome: {suggestion.author_name}\n'
            f'Título sugerido: {suggestion.title_suggested}\n'
            f'Categoria: {suggestion.category}\n\n'
            f'Motivo:\n{suggestion.reason}\n\n'
            f'Recebida em: {suggestion.created_at:%d/%m/%Y %H:%M} UTC'
        )

        subject = f'Nova sugestão de crítica: {suggestion.title_suggested}'
        sender = settings.SUGGESTIONS_FROM_EMAIL
        try:
            sent_count = send_mail(
                subject=subject,
                message=message,
                from_email=sender,
                recipient_list=[settings.SUGGESTIONS_EMAIL],
                fail_silently=False,
            )
        except Exception as error:
            logger.exception('Falha ao enviar sugestão usando o remetente configurado.')
            if sender == 'onboarding@resend.dev':
                raise SuggestionDeliveryUnavailable() from error
            try:
                sent_count = send_mail(
                    subject=subject,
                    message=message,
                    from_email='onboarding@resend.dev',
                    recipient_list=[settings.SUGGESTIONS_EMAIL],
                    fail_silently=False,
                )
            except Exception as fallback_error:
                logger.exception('Falha ao enviar sugestão usando o remetente de fallback.')
                raise SuggestionDeliveryUnavailable() from fallback_error

        if sent_count != 1:
            logger.error('O serviço de e-mail não aceitou a sugestão de crítica.')
            raise SuggestionDeliveryUnavailable()

        return Response(
            {'detail': 'Sugestão enviada com sucesso.'},
            status=status.HTTP_201_CREATED,
        )
