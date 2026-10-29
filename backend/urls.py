
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.routers import DefaultRouter
from core.views import (
    ArticleViewSet,
    CommentViewSet,
    ConfirmCommentEmailView,
    SuggestionViewSet,
)
from django_otp.admin import OTPAdminSite
#admin.site.__class__ = OTPAdminSite
path('gestao-secao-e/', admin.site.urls),

class SafePasswordResetView(auth_views.PasswordResetView):
    def form_valid(self, form):
        form.save(
            domain_override=settings.PASSWORD_RESET_DOMAIN,
            use_https=settings.PASSWORD_RESET_USE_HTTPS,
            request=self.request,
            from_email=self.from_email,
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            html_email_template_name=self.html_email_template_name,
            extra_email_context=self.extra_email_context,
        )
        return HttpResponseRedirect(self.get_success_url())

# Configurar o Roteador da API

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'suggestions', SuggestionViewSet)

urlpatterns = [

    # 🔒 FLUXO NORMAL DE RECUPERAÇÃO DE SENHA:
    path('admin/password_reset/', SafePasswordResetView.as_view(), name='admin_password_reset'), # ✨ Nome padrão do Django
    path('admin/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('admin/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('admin/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    

    # Painel Administrativo
    path('admin/', admin.site.urls),
    path('api/comments/confirm/', ConfirmCommentEmailView.as_view(), name='comment-email-confirmation'),
    path('api/', include(router.urls)) # Liga todas as rotas da API no prefixo /api/
]
