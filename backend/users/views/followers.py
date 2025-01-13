from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from users.models import User
from users.mixins import FollowersMixin
from users.utils import follow_user, process_follower_request, unfollow_user


class FollowersView(FollowersMixin):
    extra_context = {'title': 'followers'}

    def get_queryset(self):
        qs = super().get_queryset()
        queryset = qs.filter(following__to_user__slug=self.user_slug)
        return queryset


class FollowingView(FollowersMixin):
    extra_context = {'title': 'following'}

    def get_queryset(self):
        qs = super().get_queryset()
        queryset = qs.filter(followers__from_user__slug=self.user_slug)
        return queryset


class FollowUserView(View):

    def post(self, request, user_slug):
        from_user = request.user
        to_user = User.objects.get(slug=user_slug)
        response = follow_user(from_user, to_user)
        return JsonResponse({'status': response})


class UnfollowUserView(View):

    def delete(self, request, user_slug):
        from_user = request.user
        to_user = User.objects.get(slug=user_slug)
        response = unfollow_user(from_user, to_user)
        return JsonResponse({'status': response})


class AcceptFollowerView(View):

    def post(self, request, user_slug):
        response = process_follower_request(user_slug, request.user, 'accept')
        if response == 'Accepted':
            return redirect('users:actions')
        return JsonResponse({'status': response})


class RejectFollowerView(View):

    def post(self, request, user_slug):
        response = process_follower_request(user_slug, request.user, 'reject')
        if response == 'Rejected':
            return redirect('users:actions')
        return JsonResponse({'status': response})
