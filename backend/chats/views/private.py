from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.views import View
from django.views.generic.list import ListView
from django.db.models import Prefetch

from chats.mixins import ChatMixin
from chats.models import PrivateChat
from users.models import User


class PrivateChatsView(ListView):
    template_name = 'chats/private_chats.html'
    context_object_name = 'chats'

    def get_queryset(self):
        chats = (
            PrivateChat.objects.annotated().
            filter(users__in=[self.request.user]).
            prefetch_related(Prefetch(
                'users',
                queryset=User.objects.exclude(id=self.request.user.id),
                to_attr='receivers'
            ))
        )
        return chats


class PrivateChatView(ChatMixin):
    model = PrivateChat
    pk_url_kwarg = 'chat_id'
    url_name = 'private_chat'
    context_object_name = 'chat'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        user = request.user
        if user not in self.object.users.all():
            raise PermissionDenied("You can't enter this chat")
        return response


class CreatePrivateChatView(View):
    def post(self, request, user_slug):
        user = User.objects.get(slug=user_slug)
        obj = PrivateChat.objects.create()
        obj.users.set([request.user, user])
        return redirect('chats:private_chat', obj.id)
