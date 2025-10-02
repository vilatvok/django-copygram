from django.db import models
from django.db.models.functions import Concat
from tree_queries.query import TreeQuerySet


class PostManager(models.Manager):
    def annotated(self):
        from blogs.models import PostMedia

        subquery = PostMedia.objects.filter(post=models.OuterRef('pk'))
        objs = self.exclude(archived=True).annotate(
            likes_count=models.Count('likes'),
            file=Concat(
                models.Value('/media/'),
                models.Subquery(subquery.values('file')[:1]),
                output_field=models.CharField()
            )
        ).select_related('owner', 'owner__privacy')
        return objs


class CommentQuerySet(TreeQuerySet):
    def with_likes(self):
        return self.annotate(likes_count=models.Count('likes'))
