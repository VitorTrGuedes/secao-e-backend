from django.contrib import admin
from .models import Article, Comment, Suggestion

# Registro de Modelos para teste da API

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'post_type', 'rating', 'created_at')
    list_filter = ('category', 'post_type')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)} # Preenche o slug automaticamente quando você digita o título!


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'email', 'article', 'is_approved', 'created_at')
    list_editable = ('is_approved',)
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author_name', 'email', 'opinion')


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('title_suggested', 'author_name', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('title_suggested', 'author_name', 'reason')
  

