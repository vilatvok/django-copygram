from asgiref.sync import sync_to_async
from unittest.mock import patch
from django.test import TestCase, override_settings, TransactionTestCase
from django.urls import reverse
from django.conf import settings
from channels.layers import get_channel_layer
from channels.testing.websocket import WebsocketCommunicator

from users.models import User
from chats.consumers import ChatConsumer
from chats.models import PrivateChat, GroupChat

# TODO: Rewrite the tests using pytest

@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class PrivateChatTestCase(TestCase):

    @classmethod
    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUpTestData(cls, mock_delete_scheduler):
        cls.user = User.objects.create_user(
            username='admin',
            password='12345rtx',
            email='kvydyk@gmail.com',
        )
        cls.another_user = User.objects.create_user(
            username='john',
            password='12345rtx',
            email='john@gmail.com',
        )
        
        cls.fake_user = User.objects.create_user(
            username='fake',
            password='12345rtx',
            email='fake@gmail.com',
        )

        cls.chat = PrivateChat.objects.create()
        cls.chat.users.set([cls.user, cls.another_user])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_chats(self):
        response = self.client.get(reverse('chats:private_chats'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['chats'].count(), 1)

    def test_create_chat(self):
        url = reverse('chats:create_private', args=[self.fake_user.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.chats.count(), 2)


class GroupChatTestCase(TestCase):

    @classmethod
    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUpTestData(cls, mock_delete_scheduler):
        cls.user = User.objects.create_user(
            username='admin',
            password='12345rtx',
            email='kvydyk@gmail.com',
        )
        cls.second_user = User.objects.create_user(
            username='john',
            password='12345rtx',
            email='john@gmail.com',
        )
        
        cls.third_user = User.objects.create_user(
            username='fake',
            password='12345rtx',
            email='fake@gmail.com',
        )

        cls.chat = GroupChat.objects.create(owner=cls.user, name='Test room')
        cls.chat.users.set([cls.user, cls.second_user])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_groups(self):
        response = self.client.get(reverse('chats:groups'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['groups'].count(), 1)

    def test_create_group(self):
        url = reverse('chats:create_group')
        data = {
            'name': 'Test room 2',
            'users': [self.second_user.id, self.third_user.id],
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(GroupChat.objects.filter(name='Test room 2').exists())

    def test_get_group(self):
        url = reverse('chats:group_chat', args=[self.chat.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_group_members(self):
        url = reverse('chats:group_users', args=[self.chat.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['users'].count(), 2)

    def test_edit_group(self):
        url = reverse('chats:edit_group', args=[self.chat.id])
        data = {
            'name': 'Test room 2',
            'users': [self.user.id, self.second_user.id],
            'add_users': [self.third_user.id]
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.chat.users.count(), 3)
        self.assertIn(self.third_user, self.chat.users.all())

    def test_delete_group(self):
        url = reverse('chats:delete_group', args=[self.chat.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(GroupChat.objects.filter(id=self.chat.id).exists())


class ConsumerTestCase(TransactionTestCase):

    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUp(self, mock_scheduler):
        self.user = User.objects.create_user(
            username='admin',
            password='12345rtx',
            email='admin@gmail.com',
        )
        self.second_user = User.objects.create_user(
            username='john',
            password='12345rtx',
            email='john@gmail.com',
        )
        self.third_user = User.objects.create_user(
            username='fake',
            password='12345rtx',
            email='fake@gmail.com',
        )

        self.chat = PrivateChat.objects.create()
        self.chat.users.set([self.user, self.second_user])

        self.group = GroupChat.objects.create(owner=self.user, name='Test room')
        self.group.users.set([self.user, self.second_user, self.third_user])

    async def connect_communicator(self):
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f'/ws/chat/{self.chat.id}/',
        )
        communicator.scope['user'] = self.user
        communicator.scope['url_route'] = {'kwargs': {'chat_id': self.chat.id}}
        communicator.scope['channel_layer'] = get_channel_layer()

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_send_message(self):
        communicator = await self.connect_communicator()

        # Send event
        message = {
            'action': 'send_message',
            'user': self.user.username,
            'url': 'chat',
            'chat': self.chat.id,
            'avatar': 'staticfiles/users/img/user.png',
            'message': 'Hello',
        }
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from()

        self.assertEqual(response['action'], 'send_message')

        msgs = await sync_to_async(self.chat.messages.count)()
        self.assertEqual(msgs, 1)

        # Disconnect from the server
        await communicator.disconnect()

    async def test_clear_chat(self):
        communicator = await self.connect_communicator()

        # Send event
        message = {
            'action': 'clear_chat',
            'url': 'chat',
            'chat': self.chat.id,
        }
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from()

        self.assertEqual(response['action'], 'clear_chat')

        msgs = await sync_to_async(self.chat.messages.count)()
        self.assertEqual(msgs, 0)

        # Disconnect from the server
        await communicator.disconnect()

    async def test_remove_chat(self):
        communicator = await self.connect_communicator()

        # Send event
        message = {'action': 'remove_chat', 'chat': self.chat.id}

        await communicator.send_json_to(message)
        response = await communicator.receive_json_from()
        self.assertEqual(response['action'], 'remove_chat')

        chats = await sync_to_async(self.user.private_chats.count)()
        self.assertEqual(chats, 0)

        await communicator.disconnect()
    
    async def test_leave_group(self):
        communicator = await self.connect_communicator()

        # Send event
        message = {
            'action': 'leave_group',
            'chat': self.group.id,
            'user': self.user.username,
        }
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from()
        self.assertEqual(response['action'], 'leave_group')

        user_groups = await sync_to_async(self.user.groups.count)()
        self.assertEqual(user_groups, 0)

        await communicator.disconnect()
