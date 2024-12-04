from django.db import transaction, models
from django.core.cache import cache

from common.utils import create_action, get_blocked_users, redis_client
from blogs.models import Post, PostMedia, Story, UninterestingPost
from users.models import User
from users.recommendations import Recommender


def like_post(user: User, post: Post):
    if post.likes.filter(id=user.id).exists():
        status = 'Already liked'
    else:
        with transaction.atomic():
            post.likes.add(user)
            if user != post.owner:
                create_action(user, 'liked post', post, post.file)
        status = 'Liked'
    return status


def unlike_post(user: User, post: Post):
    if post.likes.filter(id=user.id).exists():
        post.likes.remove(user)
        status = 'Unliked'
    else:
        status = 'Post not liked'
    return status


def save_post(user: User, post: Post):
    if post.saved.filter(id=user.id).exists():
        status = 'Already saved'
    else:
        post.saved.add(user)
        status = 'Saved'
    return status


def unsave_post(user: User, post: Post):
    if post.saved.filter(id=user.id).exists():
        post.saved.remove(user)
        status = 'Unsaved'
    else:
        status = 'Post not saved'
    return status


def get_posts(user: User):
    blocked_users = get_blocked_users(user)
    posts = (
        Post.objects.annotated().
        exclude(owner__in=blocked_users).
        prefetch_related('tags').
        order_by('?')
    )
    return posts


def get_explore_posts(user: User | None = None):
    if user is None:
        posts = Post.objects.annotated().prefetch_related('tags').order_by('?')
    else:
        blocked_users = get_blocked_users(user)
        posts_ids = Recommender(user).get_posts_ids()

        vip_users = redis_client.smembers('active_vip_users')
        posts = (
            Post.objects.annotated().
            annotate(
                is_vip=models.Case(
                    models.When(owner_id__in=vip_users, then=models.Value(True)),
                    default=models.Value(False),
                    output_field=models.BooleanField()
                )
            ).
            filter(id__in=posts_ids).
            exclude(owner__in=blocked_users).
            prefetch_related('tags').
            order_by('-is_vip', '?')
        )
    return posts


def get_feed_posts(user_id: int):
    posts = (
        Post.objects.annotated().
        filter(owner__followers__from_user_id=user_id).
        prefetch_related('tags').
        order_by('-created_at')
    )
    return posts


def get_archived_posts(user_id: int):
    key = 'archived_posts'
    posts = cache.get(key)
    if posts is None:
        subquery = PostMedia.objects.filter(post=models.OuterRef('pk'))
        posts = (
            Post.objects.
            filter(owner_id=user_id, archived=True).
            annotate(
                likes_count=models.Count('likes'),
                file=models.Subquery(subquery.values('file')[:1]),
            ).
            select_related('owner', 'owner__privacy')
        )
        cache.set(key, posts, 60 * 60)
    return posts


def get_archived_stories(user_id: int):
    key = 'archived_stories'
    stories = cache.get(key)
    if stories is None:
        stories = Story.objects.filter(owner_id=user_id, archived=True)
        cache.set(key, stories, 60 * 60)
    return stories


def get_uninteresting_posts(user_id: int):
    key = 'uninteresting_posts'
    posts = cache.get(key)
    if posts is None:
        un_posts = UninterestingPost.objects.filter(user_id=user_id)
        posts_ids = un_posts.values_list('post_id', flat=True)
        posts = Post.objects.annotated().filter(id__in=posts_ids)
        cache.set(key, posts, 60 * 60)
    return posts
