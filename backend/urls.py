
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import ArticleViewSet, CommentViewSet, SuggestionViewSet

# Configurar o Roteador da API

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'suggestions', SuggestionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)) # Liga todas as rotas da API no prefixo /api/
]
