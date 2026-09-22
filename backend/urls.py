
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from rest_framework.routers import DefaultRouter
from core.views import ArticleViewSet, CommentViewSet, SuggestionViewSet



def health_check(request):
    return HttpResponse("OK", content_type="text/plain")

# Configurar o Roteador da API

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'suggestions', SuggestionViewSet)

urlpatterns = [
    # 💓 Rota de saúde para manter o Render acordado
    path('health/', health_check, name='health_check'),

    # 🔒 FLUXO NORMAL DE RECUPERAÇÃO DE SENHA:
    path('admin/password_reset/', auth_views.PasswordResetView.as_view(), name='admin_password_reset'), # ✨ Nome padrão do Django
    path('admin/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('admin/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('admin/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    

    # Painel Administrativo
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)) # Liga todas as rotas da API no prefixo /api/
]
