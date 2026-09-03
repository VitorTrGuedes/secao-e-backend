from rest_framework import serializers
from .models import Article, Comment, Suggestion

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'article', 'author_name', 'opinion', 'created_at']


class ArticleSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField


    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'category', 'post_type', 'image_url', 'content', 'rating', 'created_at', 'comments']

    def get_comments(self, obj):
        return CommentSerializer(obj.comments.filter(is_approved=True), many=True).data


class SuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suggestion
        fields = ['id', 'author_name', 'title_suggested', 'category', 'reason', 'created_at']