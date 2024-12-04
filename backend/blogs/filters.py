from django_filters import rest_framework as filters

from blogs.models import Post


class PostFilter(filters.FilterSet):
    created_at = filters.DateRangeFilter()

    class Meta:
        model = Post
        fields = {
            'owner__username': ['icontains'],
            'description': ['istartswith'],
        }
