from django.db import models
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.contrib.postgres.search import (
    SearchVector,
    SearchQuery,
    SearchRank,
)
from taggit.models import Tag

from common.utils import redis_client, get_blocked_users
from users.forms import ReportForm
from users.models import User, Action, Follower
from blogs.models import Post


class ActionsView(ListView):
    template_name = 'users/actions.html'
    context_object_name = 'actions'

    def get_queryset(self):
        user = self.request.user
        actions = Action.objects.filter(
            models.Q(post__owner=user) |
            models.Q(user=user),
        ).select_related('owner', 'content_type')
        redis_client.delete(f'user:{user.username}:unread_actions')
        return actions


class ClearActionsView(View):

    def post(self, request):
        user = request.user
        Action.objects.filter(
            models.Q(post__owner=user) |
            models.Q(user=user),
        ).delete()
        return redirect('users:actions')


class DeleteActionView(View):

    def delete(self, request, action_id):
        user = request.user
        action = Action.objects.get(id=action_id)
        error_response = JsonResponse({'status': "You can't delete"})
        ok_response = JsonResponse({'status': 'Ok'})
        try:
            check_action = action.target.owner
        except AttributeError:
            check_action = action.target
            if user != check_action:
                return error_response
            action.delete()
            return ok_response
        else:
            if user != check_action:
                return error_response
            action.delete()
            return ok_response


class ActivityView(ListView):
    template_name = 'users/activity.html'
    context_object_name = 'data'

    def get_queryset(self):
        user = self.request.user
        posts = Post.objects.annotated().filter(likes=user)
        comments = (
            user.comments.exclude(post__archived=True).
            select_related('post', 'owner')
        )
        return {'posts': posts, 'comments': comments}


class SavedPostsView(ListView):
    template_name = 'blogs/posts.html'
    context_object_name = 'posts'

    def get_queryset(self):
        user = self.request.user
        posts = Post.objects.annotated().filter(saved=user)
        return posts


class SearchView(ListView):
    """Search users or posts (by description) in search field."""

    template_name = 'users/search.html'
    context_object_name = 'data'

    def get_queryset(self):
        request = self.request
        q = request.GET.get('q')
        users_queryset = self.get_users_queryset(q, request.user)
        tags_queryset = self.get_tags_queryset(q)
        return {'users': users_queryset, 'tags': tags_queryset}

    def get_users_queryset(self, q: str, user: User):
        blocked_users = get_blocked_users(user)
        is_followed = Follower.objects.filter(
            from_user=user,
            to_user=models.OuterRef('pk'),
        )

        query = SearchQuery(q)
        search_vector = SearchVector('username', 'first_name', 'last_name')
        users_queryset = (
            User.objects.exclude(id__in=blocked_users).
            annotate(
                search=search_vector,
                rank=SearchRank(search_vector, query),
                followers_count=models.Count('followers'),
                is_followed=models.Exists(is_followed),
            ).filter(search=query).order_by("-rank")
        )

        # * Elasticsearch
        # Get users from Elasticsearch
        # search_by_username = Q('prefix', username=q)
        # search_by_first_name = Q('prefix', first_name=q)
        # search_by_last_name = Q('prefix', last_name=q)
        # should = [
        #     search_by_username,
        #     search_by_first_name,
        #     search_by_last_name,
        # ]

        # users_queryset = (
        #     UserDocument.search().
        #     query('bool', should=should).
        #     filter('bool', must_not=[Q('term', username=user.username)])
        # )
        # users_result = users_queryset.execute()
        # users_ids = [int(user.meta.id) for user in users_result]

        # # Get users from database
        # users_queryset = (
        #     User.objects.exclude(id__in=blocked_users).
        #     filter(id__in=users_ids).
        #     annotate(
        #         followers_count=models.Count('followers'),
        #         is_followed=models.Exists(is_followed),
        #     ).order_by('-followers_count')
        # )
        return users_queryset

    def get_tags_queryset(self, q: str):
        query = SearchQuery(q)
        search_vector = SearchVector('name')
        tags_queryset = Tag.objects.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, query),
        ).filter(search=query).order_by("-rank")

        # * Elasticsearch
        # search_by_name = Q('prefix', name=q)
        # tags_queryset = (
        #     TagDocument.search().
        #     query('bool', should=[search_by_name])
        # )
        # tags_result = tags_queryset.execute()
        # tags_ids = [int(tag.meta.id) for tag in tags_result]
        # tags_queryset =Tag.objects.filter(id__in=tags_ids)
        return tags_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requests = []
        for user in context['data']['users']:
            key = f'user:{user.username}:requests'
            user_requests = redis_client.smembers(key)
            if self.request.user.username in user_requests:
                requests.append(user.id)
        context['user_requests'] = requests
        return context


class CreateReportView(CreateView):
    form_class = ReportForm
    template_name = 'users/create_report.html'
    slug_url_kwarg = 'user_slug'

    def get_success_url(self):
        return reverse('users:profile', args=[self.kwargs['user_slug']])

    def form_valid(self, form):
        user = User.objects.get(slug=self.kwargs['user_slug'])
        f = form.save(commit=False)
        f.report_from = self.request.user
        f.report_on = user
        return super().form_valid(form)
