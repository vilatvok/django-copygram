from django.conf import settings
from django_filters import rest_framework as filters

from blogs.models import Post
from blogs.utils import SearchEngineAI


class PostFilter(filters.FilterSet):
    created_at = filters.DateRangeFilter()
    description = filters.CharFilter(method='filter_description')

    class Meta:
        model = Post
        fields = {
            'owner__username': ['icontains'],
        }

    def filter_description(self, queryset, name, value):
        engine = SearchEngineAI(api_key=settings.GEMINI_API_KEY)        
        qs = engine.get_posts(value)
        return qs
