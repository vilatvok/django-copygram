from django.db import transaction, IntegrityError, models
from django.utils.decorators import method_decorator
from taggit.models import Tag
from rest_framework import status
from rest_framework.viewsets import ViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from common.utils import cache_queryset, create_action, get_blocked_users
from common.viewsets import (
    CustomModelViewSet,
    NonUpdateViewSet,
    ListModelViewSet,
)
from blogs import utils
from blogs.filters import PostFilter
from blogs.models import Comment, Story, UninterestingPost
from blogs.api import serializers
from blogs.permissions import IsOwner, PostAuthenticated
from users.models import Follower


class PostViewSet(CustomModelViewSet):
    permission_classes = [PostAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PostFilter

    def get_queryset(self):
        return utils.get_explore_posts()

    def list(self, request, *args, **kwargs):

        # * Amount of posts depends on user's authentication status
        user = request.user
        if user.is_authenticated:
            queryset = utils.get_explore_posts(user)
        else:
            queryset = self.get_queryset()

        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action in ['list', 'feed', 'create']:
            return serializers.PostSerializer
        elif self.action in ['update', 'partial_update']:
            return serializers.PostUpdateSerializer
        return serializers.PostDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        owner_privacy = post.owner.privacy
        excluded = []
        if post.owner != request.user:
            is_follower = Follower.objects.filter(
                from_user=request.user,
                to_user=post.owner,
            ).exists()

            # check if user hid comments
            if owner_privacy.comments == 'followers' and not is_follower:
                excluded.append('comments')
            elif owner_privacy.comments == 'nobody':
                excluded.append('likes')

            # check if user hid likes count
            if owner_privacy.likes == 'followers' and not is_follower:
                excluded.append('likes')
            elif owner_privacy.likes == 'nobody':
                excluded.append('likes')

        serializer = self.get_serializer(instance=post, exclude=excluded)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def feed(self, request):
        queryset = utils.get_feed_posts(request.user.id)
        serializer = self.get_serializer(
            instance=queryset,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        post = self.get_object()
        post.archived = True
        post.save()
        return Response({'status': 'Archived'}, status.HTTP_206_PARTIAL_CONTENT)

    @action(detail=True, methods=['post'], url_path='comment')
    def add_comment(self, request, pk=None):
        user = request.user
        post = self.get_object()
        comment = serializers.CommentSerializer(
            data=request.data,
            context={'request': request},
        )
        comment.is_valid(raise_exception=True)
        with transaction.atomic():
            comment.save(owner=user, post=post)
            if user != post.owner:
                create_action(user, 'commented on', post, post.file)
        return Response(comment.data)

    @action(
        detail=True,
        methods=['post'],
        url_path='reply-to-comment/(?P<comment_id>[^/.]+)',
    )
    def reply_to_comment(self, request, comment_id, pk=None):
        user = request.user
        post = self.get_object()
        comment_serializer = serializers.CommentSerializer(
            data=request.data,
            context={'request': request},
        )
        comment_serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            comment = Comment.objects.filter(id=comment_id, post=post)
            if comment.exists():
                comment_serializer.save(
                    owner=user,
                    post=post,
                    parent=comment[0],
                )
                if user != post.owner:
                    create_action(user, 'replied to comment', post, post.file)
            else:
                return Response(
                    data={'status': 'Comment not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(comment_serializer.data)

    @action(
        detail=True,
        methods=['post'],
        url_path='like-comment/(?P<comment_id>[^/.]+)',
    )
    def like_comment(self, request, comment_id, pk=None):
        user = request.user
        post = self.get_object()
        comment = Comment.objects.filter(id=comment_id, post=post)
        if comment.exists():
            comment = comment[0]
            if comment.likes.filter(id=user.id).exists():
                comment.likes.remove(user)
                state = 'Unliked'
            else:
                with transaction.atomic():
                    comment.likes.add(user)
                    if user != post.owner:
                        create_action(user, 'liked comment', post, post.file)
                state = 'Liked'
            return Response({'status': state}, status.HTTP_201_CREATED)
        else:
            return Response(
                data={'status': 'Comment not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(
        detail=True,
        methods=['delete'],
        url_path='delete-comment/(?P<comment_id>[^/.]+)',
    )
    def delete_comment(self, request, comment_id, pk=None):
        post = self.get_object()
        comment = Comment.objects.get(id=comment_id)
        if comment.owner != request.user and post.owner != request.user:
            return Response({'status': 'You cant delete this comment'})
        comment.delete()
        return Response({'status': 'deleted'}, status.HTTP_204_NO_CONTENT)

    @staticmethod
    def generate_action_response(response):
        data = {'status': response}
        if response in ['Liked', 'Unliked', 'Saved', 'Unsaved']:
            return Response(data, status.HTTP_200_OK)
        else:
            return Response(data, status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='like')
    def add_like(self, request, pk=None):
        return self.get_action_response(request, utils.like_post)

    @action(detail=True, methods=['delete'], url_path='unlike')
    def remove_like(self, request, pk=None):
        return self.get_action_response(request, utils.unlike_post)

    @action(detail=True, methods=['post'], url_path='save')
    def save_post(self, request, pk=None):
        return self.get_action_response(request, utils.save_post)

    @action(detail=True, methods=['delete'], url_path='unsave')
    def unsave_post(self, request, pk=None):
        return self.get_action_response(request, utils.unsave_post)

    @action(detail=True, methods=['post'], url_path='add-uninteresting')
    def add_uninteresting(self, request, pk=None):
        user = request.user
        try:
            UninterestingPost.objects.create(user=user, post_id=pk)
            return Response({'status': 'Added'}, status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {'status': 'Already added'},
                status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='remove-uninteresting')
    def remove_uninteresting(self, request, pk=None):
        user = request.user
        un_post = UninterestingPost.objects.filter(user=user, post_id=pk)
        if un_post.exists():
            un_post.delete()
            return Response({'status': 'Removed'}, status.HTTP_200_OK)
        return Response({'status': 'Not found'}, status.HTTP_404_NOT_FOUND)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(
            instance=queryset,
            many=True,
            exclude=['name', 'posts'],
        )
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, exclude=['url'])
        return Response(serializer.data)


class StoryViewSet(NonUpdateViewSet):
    serializer_class = serializers.StorySerializer
    permission_classes = [IsAuthenticated, IsOwner]

    @method_decorator(cache_queryset('stories'))
    def get_queryset(self):
        blocked_users = get_blocked_users(self.request.user)
        stories = Story.objects.exclude(
            models.Q(owner__in=blocked_users) |
            models.Q(archived=True),
        ).select_related('owner')
        return stories

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ArchiveViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def get_posts_queryset(self):
        return utils.get_archived_posts(self.request.user.id)

    def get_stories_queryset(self):
        return utils.get_archived_stories(self.request.user.id)

    @action(detail=False)
    def posts(self, request, pk=None):
        posts = self.get_posts_queryset()
        serializer = serializers.ArchivePostsSerializer(
            instance=posts,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)

    @action(detail=False)
    def stories(self, request, pk=None):
        stories = self.get_stories_queryset()
        serializer = serializers.ArchiveStorySerializer(
            instance=stories,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['get', 'delete', 'post'],
        url_path='posts/(?P<pk>[^/.]+)',
    )
    def get_post(self, request, pk=None):
        post = self.get_posts_queryset().get(pk=pk)
        if request.method == 'GET':
            serializer = serializers.ArchivePostSerializer(
                instance=post,
                context={'request': request},
            )
            return Response(serializer.data)
        elif request.method == 'POST':
            post.archived = False
            post.save()
        elif request.method == 'DELETE':
            post.delete()
            return Response({'status': 'Deleted'}, status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get', 'delete', 'post'],
        url_path='stories/(?P<pk>[^/.]+)',
    )
    def get_story(self, request, pk=None):
        story = self.get_stories_queryset().get(pk=pk)
        if request.method == 'GET':
            serializer = serializers.ArchiveStorySerializer(
                instance=story,
                context={'request': request},
            )
            return Response(serializer.data)
        elif request.method == 'POST':
            story.archived = False
            story.save()
            return Response({'status': 'Restored'}, status.HTTP_204_NO_CONTENT)
        elif request.method == 'DELETE':
            story.delete()
            return Response({'status': 'Deleted'}, status.HTTP_204_NO_CONTENT)


class UninterestingPostViewSet(ListModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.PostSerializer

    def get_queryset(self):
        return utils.get_uninteresting_posts(self.request.user.id)
