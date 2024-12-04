from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.viewsets import NonUpdateViewSet
from chats.mixins import ChatAPIMixin
from chats.permissions import IsGroupOwner, IsPrivateMember
from chats.models import GroupChat, PrivateChat
from chats.api.serializers import (
    PrivateChatSerializer,
    PrivateChatsSerializer,
    GroupChatSerializer,
    GroupChatsSerializer,
)


class GroupChatViewSet(ChatAPIMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsGroupOwner]

    def get_queryset(self):
        groups = (
            GroupChat.objects.annotated().
            filter(users__in=[self.request.user]).
            select_related('owner').prefetch_related('users')
        )
        return groups

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupChatsSerializer
        return GroupChatSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PrivateChatViewSet(ChatAPIMixin, NonUpdateViewSet):
    permission_classes = [IsAuthenticated, IsPrivateMember]

    def get_queryset(self):
        chats = (
            PrivateChat.objects.annotated().
            filter(users__in=[self.request.user]).
            prefetch_related('users')
        )
        return chats

    def get_serializer_class(self):
        if self.action == 'list':
            return PrivateChatsSerializer
        return PrivateChatSerializer
