
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from core.views import ArticleViewSet, CommentViewSet, SuggestionViewSet
from django_otp.admin import OTPAdminSite
#admin.site.__class__ = OTPAdminSite
path('gestao-secao-e/', admin.site.urls),

# Configurar o Roteador da API

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'suggestions', SuggestionViewSet)

urlpatterns = [
    # 🔒 ROTAS DE RECUPERAÇÃO DE SENHA DO ADMIN:
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('recuperar-senha/confirmar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('recuperar-senha/concluido/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    

    # Painel Administrativo
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)) # Liga todas as rotas da API no prefixo /api/
]
