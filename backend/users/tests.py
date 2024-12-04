from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.conf import settings

from common.utils import create_action
from users.models import Block, Follower, User, Action
from users.utils import generate_reset_password_params
from blogs.models import Post

# TODO: Rewrite the tests using pytest

@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class UserTestCase(TestCase):

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

    def setUp(self):
        self.client.force_login(self.user)

    @patch('users.views.auth.send_reset_email', return_value=None)
    def test_create_user(self, mock_send_email):
        self.client.logout()

        data = {
            'username': 'taras',
            'email': 'kovtalivt@gmail.com',
            'password1': '12345rtx',
            'password2': '12345rtx'
        }
        response = self.client.post(reverse('users:register'), data)
        self.assertEqual(response.status_code, 302)

    @patch('users.signals.delete_account_scheduler', return_value=None)
    def test_email_verification(self, mock_scheduler):
        self.client.logout()

        user = User.objects.create_user(
            username='taras',
            password='12345rtx',
            email='kovtalivt@gmail.com'
        )
        uidb64, token = generate_reset_password_params(user)

        url = reverse('users:register_confirm', args=[uidb64, token])
        response = self.client.get(url)
        users = User.objects.all()
        user_is_active = User.objects.get(username=user.username).is_active

        self.assertTrue(mock_scheduler.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user_is_active, True)
        self.assertEqual(users.count(), 3, users)

    def test_get_user(self):
        slug = self.user.slug
        response = self.client.get(reverse('users:profile', args=[slug]))
        self.assertEqual(response.status_code, 200)

    def test_edit_user(self):
        data = {
            'username': 'admin',
            'first_name': 'adminik',
            'last_name': '',
            'email': 'kvydyk@gmail.com',
            'gender': 'male'
        }
        response = self.client.post(reverse('users:edit_profile'), data)

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.first_name, 'adminik')
    
    def test_edit_settings(self):
        data = {
            'private_account': True,
            'likes': 'everyone',
            'comments': 'everyone',
            'online_status': 'everyone',
        }
        response = self.client.post(reverse('users:edit_settings'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.privacy.private_account, True)
    
    def test_delete_user(self):
        response = self.client.post(reverse('users:delete_account'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_change_password(self):
        url = reverse('users:change_password')
        data = {
            "old_password": '12345rtx',
            "new_password1": '123456rtx',
            "new_password2": '123456rtx',
        }
        response = self.client.post(url, data)

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.user.check_password('123456rtx'))
    
    @patch('users.views.auth.send_reset_email', return_value=None)
    def test_reset_password(self, mock_send_email):
        self.client.logout()

        # Reset password
        url = reverse('users:password_reset')
        data = {'email': self.user.email}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Confirm user account
        url = reverse('users:password_user_confirm')
        data = {'confirm': 'yes'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(mock_send_email.called)
        self.assertRedirects(response, reverse('users:password_reset_done'))

    def test_reset_password_confirm(self):
        self.client.logout()

        uidb64, token = generate_reset_password_params(self.user)
        url = reverse('users:password_reset_confirm', args=[uidb64, token])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        data = {'new_password1': '12345rty', 'new_password2': '12345rty'}
        redirect_response = self.client.post(response.url, data)
        self.assertEqual(redirect_response.status_code, 302)
        self.assertRedirects(redirect_response, reverse('users:login'))
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('12345rty'))


@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class ActionTestCase(TestCase):

    @classmethod
    @patch('blogs.signals.create_post', return_value=None)
    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUpTestData(cls, mock_post, mock_scheduler):
        cls.user = User.objects.create_user(
            username='admin',
            email='kvydyk@gmail.com',
            password='12345rtx',
        )
        cls.another_user = User.objects.create_user(
            username='taras',
            email='kovtalivt@gmail.com',
            password='12345rtx',
        )
        post = Post.objects.create(
            description='Test description',
            owner=cls.another_user,
        )
        post.likes.add(cls.user)
        create_action(cls.another_user, 'followed you', cls.user)

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_actions(self):
        response = self.client.get(reverse('users:actions'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['actions']), 1)

    def test_clear_actions(self):
        response = self.client.post(reverse('users:clear_actions'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Action.objects.count(), 0)

    def test_delete_action(self):
        a = Action.objects.first()
        url = reverse('users:delete_action', args=[a.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 0)
    
    def test_get_activity(self):
        response = self.client.get(reverse('users:activity'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['data']['posts']), 1)


@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class FollowerTestCase(TestCase):

    @classmethod
    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUpTestData(cls, mock_scheduler):
        cls.user = User.objects.create_user(
            username='admin',
            password='12345rtx',
            email='kvydyk@gmail.com',
        )
        cls.user.privacy.private_account = True
        cls.user.privacy.save()

        cls.another_user = User.objects.create_user(
            username='john',
            password='12345rtx',
            email='john@gmail.com',
        )

        fake_user = User.objects.create_user(
            username='fake',
            password='12345rtx',
            email='fake@gmail.com',
        )

        following = Follower(from_user=cls.user, to_user=fake_user)
        followers = Follower(from_user=fake_user, to_user=cls.user)
        Follower.objects.bulk_create([following, followers])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_following(self):
        url = reverse('users:following', args=[self.user.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['users']), 1)

    def test_get_followers(self):
        url = reverse('users:followers', args=[self.user.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['users']), 1)

    @patch('users.signals.recommend_users', return_value=None)
    def test_follow_user(self, mock_recommendations):
        url = reverse('users:follow', args=[self.another_user.slug])
        response = self.client.post(url)
        self.assertTrue(mock_recommendations.called)
        self.assertEqual(response.json()['status'], 'Followed')

        url = reverse('users:unfollow', args=[self.another_user.slug])
        response = self.client.delete(url)
        self.assertEqual(response.json()['status'], 'Unfollowed')
    
    @patch('users.signals.recommend_users', return_value=None)
    def test_accept_follower(self, mock_recommendations):
        self.client.logout()

        self.client.force_login(self.another_user)
        url = reverse('users:follow', args=[self.user.slug])
        response = self.client.post(url)
        self.assertEqual(response.json()['status'], 'Request was sent')

        self.client.logout()
        self.client.force_login(self.user)

        url = reverse('users:accept_follower', args=[self.another_user.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            self.another_user.id, 
            self.user.followers.values_list('from_user', flat=True),
        )

        self.assertTrue(mock_recommendations.called)

    def test_reject_follower(self):
        self.client.logout()

        self.client.force_login(self.another_user)
        url = reverse('users:follow', args=[self.user.slug])
        response = self.client.post(url)
        self.assertEqual(response.json()['status'], 'Request was sent')

        self.client.logout()
        self.client.force_login(self.user)

        url = reverse('users:reject_follower', args=[self.another_user.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(
            self.another_user.id, 
            self.user.followers.values_list('from_user', flat=True),
        )


@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class BlockTestCase(TestCase):

    @classmethod
    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUpTestData(cls, mock_scheduler):
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

        Post.objects.create(description='Test description', owner=cls.fake_user)
        Block.objects.create(from_user=cls.user, to_user=cls.fake_user)
    
    def setUp(self):
        self.client.force_login(self.user)
    
    def test_get_blocked(self):
        response = self.client.get(reverse('users:blocked'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['users'].count(), 1)
    
    def test_block_user(self):
        url = reverse('users:block', args=[self.another_user.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Block.objects.count(), 2)

        url = reverse('users:unblock', args=[self.another_user.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Block.objects.count(), 1)

    def test_get_blocked_user(self):
        url = reverse('users:profile', args=[self.fake_user.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
