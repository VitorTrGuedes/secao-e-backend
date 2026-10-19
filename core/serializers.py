from rest_framework import serializers
from .content import sanitize_article_html, split_article_source
from .models import Article, Comment, Suggestion

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'article', 'author_name', 'opinion', 'created_at']


class ArticleSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    content_html = serializers.SerializerMethodField()
    source_url = serializers.SerializerMethodField()


    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'category', 'post_type', 'author', 'image_url', 'content', 'content_html', 'source_url', 'rating', 'created_at', 'comments']

    def get_comments(self, obj):
        return CommentSerializer(obj.comments.filter(is_approved=True), many=True).data

    def get_content(self, obj):
        return split_article_source(obj.content)[0]

    def get_content_html(self, obj):
        return sanitize_article_html(obj.content)

    def get_source_url(self, obj):
        return split_article_source(obj.content)[1]


class SuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suggestion
        fields = ['id', 'author_name', 'title_suggested', 'category', 'reason', 'created_at']