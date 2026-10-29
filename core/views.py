import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Prefetch
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
from .serializers import (
    ArticleSerializer,
    CommentConfirmationSerializer,
    CommentSerializer,
    SuggestionSerializer,
)

logger = logging.getLogger(__name__)


class EmailDeliveryUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Não foi possível enviar o e-mail de confirmação. Tente novamente mais tarde.'


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
        ).prefetch_related(
            Prefetch(
                'comments',
                queryset=Comment.objects.filter(is_approved=True),
                to_attr='approved_comments',
            )
        ).order_by('-created_at')


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
        comment.save(update_fields=['email_confirmation_token', 'email_confirmation_sent_at'])

        confirmation_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/confirmar-comentario?"
            f"{urlencode({'token': token})}"
        )
        message = (
            f"Olá, {comment.author_name}!\n\n"
            "Para confirmar seu e-mail e publicar seu comentário, acesse:\n"
            f"{confirmation_url}\n\n"
            "O link expira em 24 horas. Se você não enviou este comentário, ignore esta mensagem."
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
