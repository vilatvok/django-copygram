from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.core.exceptions import PermissionDenied
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from chats.mixins import ChatMixin
from chats.models import GroupChat
from chats.forms import GroupChatForm, EditGroupChatForm
from users.models import User


class GroupChatsView(ListView):
    template_name = 'chats/groups.html'
    context_object_name = 'groups'

    def get_queryset(self):
        qs = (
            GroupChat.objects.annotated().
            filter(users__in=[self.request.user]).
            select_related('owner')
        )
        return qs


class GroupChatView(ChatMixin):
    queryset = GroupChat.objects.select_related('owner')
    pk_url_kwarg = 'group_id'
    url_name = 'group_chat'
    context_object_name = 'chat'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.user not in self.object.users.all():
            raise PermissionDenied("You can't enter this group")
        return response


class GroupChatUsersView(ListView):
    template_name = 'users/followers.html'
    context_object_name = 'users'
    pk_url_kwarg = 'group_id'

    def get_queryset(self):
        user = self.request.user
        group = GroupChat.objects.only('users').get(id=self.kwargs['group_id'])
        qs = User.objects.annotated(current_user=user).filter(group_chats=group)
        return qs


class CreateGroupChatView(CreateView):
    model = GroupChat
    form_class = GroupChatForm
    template_name = 'chats/create_group.html'

    def get_success_url(self):
        return reverse('chats:group_chat', args=[self.object.id])

    @transaction.atomic
    def form_valid(self, form):
        f = form.save(commit=False)
        f.owner = self.request.user
        response = super().form_valid(form)
        self.object.users.add(self.request.user)
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        users = User.objects.exclude(id=self.request.user.id)
        kwargs['queryset'] = users
        return kwargs


class EditGroupView(UpdateView):
    queryset = GroupChat.objects.select_related('owner').prefetch_related('users')
    form_class = EditGroupChatForm
    template_name = 'chats/edit_group.html'
    pk_url_kwarg = 'group_id'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.object.owner != request.user:
            raise PermissionDenied('You dont have permission')
        return response

    def get_success_url(self):
        return reverse('chats:group_chat', args=[self.object.id])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        users = self.object.users.all()
        add_users = User.objects.exclude(id__in=users)
        kwargs['queryset'] = users
        kwargs['queryset2'] = add_users
        return kwargs

    def form_valid(self, form):
        users = form.cleaned_data['add_users']
        response = super().form_valid(form)
        self.object.users.add(*users)
        return response


class DeleteGroupView(DeleteView):
    model = GroupChat
    template_name = 'chats/groups.html'
    success_url = reverse_lazy('chats:groups')
    pk_url_kwarg = 'group_id'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.object.owner != request.user:
            raise PermissionDenied('You dont have permission')
        return response
