from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.core.cache import cache

from common import redis_client
from blogs.models import Post, Story, UninterestingPost
from blogs.tasks import archive_story_scheduler, remove_similar_posts
from users.models import User
from users.recommendations import Recommender
from users.utils import recommend_users


@receiver(post_save, sender=Post)
def create_post(instance, created, **kwargs):
    owner = instance.owner
    cached = []

    if created:
        # get post owner followers
        followers = owner.followers.values_list('from_user_id', flat=True)
        # get the followers of the user's followers
        followers_owner_followers = User.objects.filter(
            following__to_user_id__in=followers,
        ).exclude(id=owner.id).distinct()

        # generate recommendations for followers of the user's followers
        for user in followers_owner_followers:
            r = Recommender(user)
            r.generate_recommendations()
    else:
        cached.append('saved_posts')
        if instance.archived != instance.old_archived:
            # update cache
            cached.append('archived_posts')
    cache.delete_many(cached)


@receiver(post_delete, sender=Post)
def delete_post(instance, **kwargs):
    cache.delete_many(['saved_posts', 'archived_posts'])
    owner = instance.owner

    # get post owner followers
    followers = owner.followers.values_list('from_user_id', flat=True)
    # get the followers of the user's followers
    followers_owner_followers = (
        User.objects.
        filter(following__to_user_id__in=followers).
        exclude(id=owner.id).
        values_list('username', flat=True).
        distinct()
    )

    # remove post views rank
    redis_client.zrem('post_rank', instance.id)

    # remove post from recommendations
    for username in followers_owner_followers:
        user_key = f'user:{username}:posts_recommendations'
        if instance.id in redis_client.smembers(user_key):
            redis_client.srem(user_key, instance.id)


@receiver(post_save, sender=Story)
def archive_story(instance, created, **kwargs):
    cached = ['stories']
    if created:
        archive_story_scheduler(
            story_id=instance.id,
            story_date=instance.created_at,
        )
    else:
        cached.append('archived_stories')
    cache.delete_many(cached)


@receiver(post_delete, sender=Story)
def archive_story_on_delete(**kwargs):
    cache.delete_many(['stories', 'archived_stories'])


@receiver(post_save, sender=UninterestingPost)
def add_uninteresting_post(instance, created, **kwargs):
    cache.delete('uninteresting_posts')
    if created:
        r = Recommender(instance.user)
        recommended = r.get_posts_ids()

        # get instance data
        image = instance.post.files.first().file
        description = instance.post.description
        data = [{
            'file': str(image),
            'description': description,
        }]

        posts = list(
            Post.objects.annotated().
            filter(id__in=recommended).
            values('id', 'description', 'file')
        )

        if posts:
            remove_similar_posts.delay(instance.user.username, data, posts)


@receiver(post_delete, sender=UninterestingPost)
def remove_uninteresting_post(instance, **kwargs):
    cache.delete('uninteresting_posts')
    recommend_users(instance.user)
