from django.views.generic.list import ListView

from common.utils import redis_client
from users.models import User
from users.utils import get_users


class FollowersMixin(ListView):
    template_name = 'users/followers.html'
    context_object_name = 'users'
    slug_url_kwarg = 'user_slug'

    @property
    def user_slug(self):
        return self.kwargs['user_slug']

    def get_queryset(self):
        user = self.request.user
        queryset = get_users(user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_slug = self.kwargs['user_slug']
        context['current_user'] = User.objects.get(slug=user_slug)
        authenticated_user = self.request.user
        requests = []
        for user in context['users']:
            key = f'user:{user.username}:requests'
            user_requests = redis_client.smembers(key)
            if authenticated_user.username in user_requests:
                requests.append(user.id)

        context['user_requests'] = requests
        return context
