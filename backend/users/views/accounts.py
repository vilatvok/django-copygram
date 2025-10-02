from django.http import Http404
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, DeleteView
from django.views.generic.list import ListView
from two_factor.utils import default_device

from common.utils import redis_client
from users.forms import UserEditForm, UserPrivacyForm
from users.models import User, UserPrivacy
from users.utils import block_user, get_user_posts, get_users, unblock_user
from users.recommendations import Recommender
from blogs.models import Story


class ProfileView(DetailView):
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'user'
    slug_url_kwarg = 'user_slug'

    def get_queryset(self):
        user = self.request.user
        queryset = get_users(user).select_related('privacy')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        current_user = self.request.user

        context['posts'] = get_user_posts(user_id=user.id)
        context['stories'] = (
            Story.objects.filter(owner=user).
            exclude(archived=True).
            select_related('owner')
        )

        # handle follow requests
        key = f'user:{user.username}:requests'
        user_requests = redis_client.smembers(key)
        if str(current_user.username) in user_requests:
            context['request_to_follow'] = True
        else:
            context['request_to_follow'] = False

        # recommendations for user
        recommendations = Recommender(user).get_follows_ids()
        context['recommendations'] = User.objects.filter(id__in=recommendations)
        return context


class DeleteProfileView(DeleteView):
    model = User
    success_url = reverse_lazy('users:login')

    def get_object(self, queryset=None):
        return self.request.user


class EditProfileView(UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'users/edit_profile.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return self.request.user.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_enable'] = True if default_device(self.object) else False
        return context


class EditSettingsView(UpdateView):
    model = UserPrivacy
    form_class = UserPrivacyForm
    template_name = 'users/settings.html'

    def get_object(self, queryset=None):
        return UserPrivacy.objects.get(user_id=self.request.user.id)

    def get_success_url(self):
        return self.request.user.get_absolute_url()


class BlockedView(ListView):
    template_name = 'users/blocked.html'
    context_object_name = 'users'

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.blocked(user=user)
        return queryset


class BlockUserView(View):

    def post(self, request, user_slug):
        user = request.user
        to_user = User.objects.get(slug=user_slug)
        response = block_user(user, to_user)
        if response == 'Already blocked':
            return Http404('User is already blocked')
        return redirect('users:profile', user.slug)


class UnblockUserView(View):

    def post(self, request, user_slug):
        user = request.user
        to_user = User.objects.get(slug=user_slug)
        response = unblock_user(user, to_user)
        if response == 'Not blocked':
            return Http404('User is not blocked')
        return redirect('users:profile', user.slug)
