import base64
import json

from django.db import transaction
from django.core.files.base import ContentFile
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from common import redis_client
from users.models import User
from chats.models import Message, PrivateChat, GroupChat, MessageImage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.chat = self.scope['url_route']['kwargs']['chat_id']
        self.chat_name = f'chat_{self.chat}'

        # Join room group
        await self.channel_layer.group_add(self.chat_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.chat_name,
            self.channel_name,
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        received_data = json.loads(text_data)

        chat = received_data.get('chat', None)
        action = received_data.get('action', None)
        url = received_data.get('url', None)
        user = received_data.get('user', None)
        message = received_data.get('message', None)
        avatar = received_data.get('avatar', None)
        files = received_data.get('files', None)

        match action:
            case 'send_message':
                data = {
                    'action': action,
                    'url': url,
                    'chat': chat,
                    'user': user,
                    'avatar': avatar,
                    'message': message,
                    'files': files,
                }
                if url == 'group_chat':
                    await self.save_group_message(chat, user, message, files)
                else:
                    await self.save_private_message(chat, user, message, files)

            case 'clear_chat':
                await self.clear_chat(url, chat)
                data = {'action': action, 'chat': chat, 'url': url}

            case 'remove_chat':
                await self.remove_chat(chat)
                data = {'action': action, 'chat': chat}

            case 'leave_group':
                await self.leave_group(chat, user)
                data = {'action': action, 'chat': chat, 'user': user}

        data['type'] = 'chat.message'
        await self.channel_layer.group_send(self.chat_name, data)

    # Receive message from room
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_group_message(self, chat_id, user, message, files):
        chat = GroupChat.objects.get(id=chat_id)
        sender = User.objects.get(username=user)
        users = chat.users.exclude(username=sender.username)

        message_id = self.save_db_message(chat, sender, message, files)
        # Add message to unread list for each user in the room
        for chat_user in users:
            redis_client.sadd(f'user:{chat_user.username}:group_unread', message_id)

    @database_sync_to_async
    def save_private_message(self, chat_id, user, message, files):
        chat = PrivateChat.objects.get(id=chat_id)
        sender = User.objects.get(username=user)
        users = chat.users.exclude(username=sender.username)

        message_id = self.save_db_message(chat, sender, message, files)
        redis_client.sadd(f'user:{users[0].username}:private_unread', message_id)

    def save_db_message(self, chat, sender, message, files):
        with transaction.atomic():
            message_obj = Message.objects.create(
                user=sender,
                chat=chat,
                content=message if message else ''
            )

            if files:
                files_list = []
                for file, name in files:
                    decoded_file = base64.b64decode(file.split(';base64,')[1])
                    content_file = ContentFile(decoded_file, name)
                    MessageImage(message=message_obj, file=content_file)

                MessageImage.objects.bulk_create(files_list)
            return message_obj.id

    @database_sync_to_async
    def clear_chat(self, url, chat_id):
        if url == 'group_chat':
            obj = GroupChat.objects.get(id=chat_id)
            obj.messages.all().delete()
        else:
            obj = PrivateChat.objects.get(id=chat_id)
            obj.messages.all().delete()

    @database_sync_to_async
    def leave_group(self, group_id, username):
        group = GroupChat.objects.get(id=group_id)
        group.users.remove(User.objects.get(username=username))
        if group.users.count() < 2:
            group.delete()

    @database_sync_to_async
    def remove_chat(self, group_id):
        group = PrivateChat.objects.get(id=group_id)
        group.delete()
