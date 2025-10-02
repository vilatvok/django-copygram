import base64
import json
import google.generativeai as genai
import google.api_core.exceptions as google_exceptions

from typing_extensions import TypedDict
from django.db import transaction, models
from django.core.cache import cache
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models.functions import Concat

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
        prefetch_related('tags').
        order_by('-is_vip', '?')
    )
    if user:
        blocked_users = get_blocked_users(user)
        posts_ids = Recommender(user).get_posts_ids()
        posts = posts.exclude(owner__in=blocked_users).filter(id__in=posts_ids)
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
                file=Concat(
                    models.Value('/media/'),
                    models.Subquery(subquery.values('file')[:1]),
                    output_field=models.CharField()
                )
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


class SearchEngineAI:

    class AiResponse(TypedDict):
        values: list[str]
    
    def __init__(self, api_key: str):
        self.model = self.create_ai_model(api_key)

    def create_ai_model(self, api_key: str):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")

    @staticmethod
    def generate_prompt(text: str) -> str:
        prompt=f"""
        Extract key parameters from this text
        that can be useful for database search.
        For example emotions or places, etc.
        Text: {text}'\n

        Use this JSON schema:

        Output = {{'values': list[str]}}
        Return: Output
        """
        return prompt

    def search(self, text: str) -> str:
        prompt = self.generate_prompt(text)
        encoded_text = base64.b64encode(text.encode()).decode()

        cache_key = f'search:{encoded_text}'
        response = cache.get(cache_key)
        if response is None:
            try:
            
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type='application/json',
                        response_schema=self.AiResponse
                    )
                )
                cache.set(cache_key, response, 60 * 60)
            except google_exceptions.InvalidArgument:
                raise ValueError('Invalid AI API key.')
            except google_exceptions.NotFound:
                raise AttributeError('Model not found.')
            except google_exceptions.ResourceExhausted:
                raise ValueError('Resource exhausted.')
        return response.text

    def get_posts(self, text: str):
        search_result = self.search(text)
        decoded = json.loads(search_result)

        filtered_search = (' | '.join(decoded['values']))
        search_query = SearchQuery(filtered_search, search_type='raw')
        search_vector = SearchVector('description')
        posts = (
            Post.objects.annotated().
            annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).
            filter(search=search_query).
            prefetch_related('tags').
            order_by('-rank')
        )
        return posts
