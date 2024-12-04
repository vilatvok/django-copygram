# -*- coding: utf-8 -*-
from django.contrib import admin

from chats.models import GroupChat, PrivateChat, Message, MessageImage


@admin.register(GroupChat)
class GroupChat(admin.ModelAdmin):
    list_display = ('id', 'owner', 'image', 'name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)


@admin.register(PrivateChat)
class PrivateChatAdmin(admin.ModelAdmin):
    list_display = ('id',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'content',
        'created_at',
        'content_type',
        'object_id',
    )
    list_filter = ('created_at',)


@admin.register(MessageImage)
class MessageImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file')
    search_fields = ('message__user__username',)
