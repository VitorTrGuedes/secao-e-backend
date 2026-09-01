from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.throttling import AnonRateThrottle
from .models import Article, Comment, Suggestion
from .serializers import ArticleSerializer, CommentSerializer, SuggestionSerializer

# Create your views here.

class PostThrottle(AnonRateThrottle):
    rate = '5/minute'

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all().order_by('-created_at')
    serializer_class = ArticleSerializer
    lookup_field = 'slug'

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    throttle_classes = [PostThrottle]
    http_method_names = ['post']

class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all()
    serializer_class = SuggestionSerializer
    throttle_classes = [PostThrottle]
    http_method_names = ['post']
