from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation,
)

from common.models import BaseModel
from chats.managers import ChatManager


class PrivateChat(models.Model):
    users = models.ManyToManyField('users.User', related_name='private_chats')
    messages = GenericRelation('chats.Message', related_query_name='private_chat')

    objects = ChatManager()


class GroupChat(BaseModel):
    owner = models.ForeignKey(
        to='users.User',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='group_owner',
    )
    image = models.ImageField(upload_to='rooms/%Y/%m/%d/', blank=True)
    name = models.CharField(max_length=50)
    users = models.ManyToManyField('users.User', related_name='group_chats')
    messages = GenericRelation('chats.Message', related_query_name='group_chat')

    objects = ChatManager()

    def __str__(self):
        return self.name


class Message(BaseModel):
    user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    content = models.TextField(blank=True)
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('groupchat', 'privatechat')}
    )
    object_id = models.PositiveIntegerField()
    chat = GenericForeignKey('content_type', 'object_id')


class MessageImage(models.Model):
    message = models.ForeignKey(
        to='chats.Message',
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='messages/%Y/%m/%d/', blank=True)
