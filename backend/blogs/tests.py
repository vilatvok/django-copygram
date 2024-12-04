from unittest.mock import patch
from django.test import TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.core.files.base import ContentFile
from taggit.models import Tag
from faker import Faker

from users.models import Follower, User
from blogs.models import Comment, Post, PostMedia, Story, UninterestingPost

# TODO: Rewrite the tests using pytest

@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class PostTestCase(TestCase):

    @classmethod
    @patch('users.signals.delete_account_scheduler', return_value=None)
    def setUpTestData(cls, mock_scheduler):
        cls.user = User.objects.create_user(
            username='admin',
            email='kvydyk@gmail.com',
            password='12345rtx',
        )
        cls.another_user = User.objects.create_user(
            username='john',
            email='john@gmail.com',
            password='12345rtx',
        )

        cls.faker = Faker()
        file_name = cls.faker.file_name(extension='jpeg')
        image = cls.faker.image()
        file = ContentFile(image, name=file_name)

        cls.post = Post.objects.create(
            description='Test description',
            owner=cls.user,
        )
        PostMedia.objects.create(file=file, post=cls.post)

        cls.another_post = Post.objects.create(
            description='Test description 2',
            owner=cls.another_user,
        )
        PostMedia.objects.create(file=file, post=cls.another_post)

        cls.comment = Comment.objects.create(
            owner=cls.another_user,
            post=cls.post,
            text='Test comment',
        )
        cls.tag = Tag.objects.create(name='test_tag')
        cls.post.tags.add(cls.tag)

    def setUp(self):
        self.client.force_login(self.user)

    @patch('users.signals.recommend_users', return_value=None)
    def test_get_feed(self, mock_recommendations):
        Follower.objects.create(from_user=self.user, to_user=self.another_user)

        self.assertTrue(mock_recommendations.called)

        response = self.client.get(reverse('blogs:feed'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['posts']), 1)

    def test_get_explore(self):
        response = self.client.get(reverse('blogs:explore'))
        self.assertEqual(response.status_code, 200)

    def test_create_post(self):
        url = reverse('blogs:create_post')

        file_name = self.faker.file_name(extension='jpeg')
        image = self.faker.image()
        file1 = ContentFile(image, name=file_name)

        file_name = self.faker.file_name(extension='jpeg')
        image = self.faker.image()
        file2 = ContentFile(image, name=file_name)

        data = {'description': 'Test description', 'files': [file1, file2]}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.posts.count(), 2)

    def test_get_post(self):
        response = self.client.get(reverse('blogs:post', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['post'].description, 'Test description')
        self.assertEqual(response.context_data['comments'].count(), 1)
    
    def test_get_saved_posts(self):
        self.user.saved.add(self.another_post)
        response = self.client.get(reverse('users:saved_posts'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['posts']), 1)

    def test_edit_post(self):
        url = reverse('blogs:edit_post', args=[self.post.id])
        data = {'description': 'New description'}
        response = self.client.post(url, data)

        self.post.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.post.description, 'New description')

    def test_like_post(self):
        p = Post.objects.annotated().first()
        url = reverse('blogs:add_like', args=[p.id])
        response = self.client.post(url)
        self.assertEqual(response.json()['status'], 'Liked')

        url = reverse('blogs:remove_like', args=[p.id])
        response = self.client.delete(url)
        self.assertEqual(response.json()['status'], 'Unliked')

    def test_save_post(self):
        url = reverse('blogs:save_post', args=[self.another_post.id])
        response = self.client.post(url)
        self.assertEqual(response.json()['status'], 'Saved')

        url = reverse('blogs:unsave_post', args=[self.another_post.id])
        response = self.client.delete(url)
        self.assertEqual(response.json()['status'], 'Unsaved')

    def test_delete_post(self):
        url = reverse('blogs:delete_post', args=[self.post.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.filter(owner=self.user).count(), 0)

    def test_get_likes(self):
        response = self.client.get(reverse('blogs:post_likes', args=[self.another_post.id]))
        self.assertEqual(response.status_code, 200)

    def test_archive_post(self):
        url = reverse('blogs:archive_post', args=[self.post.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.posts.filter(archived=True).count(), 1)

        url = reverse('blogs:restore_post', args=[self.post.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.posts.filter(archived=True).count(), 0)

    def test_get_archived_posts(self):
        self.post.archived = True
        self.post.save()

        response = self.client.get(reverse('blogs:archived_posts'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['posts']), 1)

    def test_get_archived_post(self):
        self.post.archived = True
        self.post.save()

        response = self.client.get(reverse('blogs:archived_post', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['post'].description, 'Test description')
    
    def test_get_tag_posts(self):
        response = self.client.get(reverse('blogs:tag_posts', args=[self.tag.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['posts'].count(), 1)

    @patch('blogs.signals.recommend_users', return_value=None)
    def test_process_uninteresting_post(self, mock_recommendations):
        url = reverse('blogs:add_uninteresting', args=[self.post.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.uninteresting_posts.count(), 1)

        url = reverse('blogs:remove_uninteresting', args=[self.post.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.uninteresting_posts.count(), 0)
        self.assertTrue(mock_recommendations.called)

    def test_get_uninteresting_posts(self):
        UninterestingPost.objects.create(user=self.user, post=self.post)
        response = self.client.get(reverse('blogs:uninteresting_posts'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['posts']), 1)

    def test_comment_on_post(self):
        url = reverse('blogs:add_comment', args=[self.another_post.id])
        data = {'q': 'Test comment'}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.another_post.comments.count(), 1)

    def test_delete_comment(self):
        Comment.objects.create(owner=self.user, post=self.post, text='Test comment')
        comment_id = self.post.comments.first().id
        url = reverse('blogs:delete_comment', args=[self.post.id, comment_id])
        response = self.client.delete(url)
        self.assertEqual(response.json()['status'], 'Deleted')


@override_settings(MEDIA_ROOT=settings.BASE_DIR / 'test_media')
class StoryTestCase(TestCase):

    @classmethod
    @patch('users.signals.delete_account_scheduler', return_value=None)
    @patch('blogs.signals.archive_story', return_value=None)
    def setUpTestData(cls, mock_scheduler, mock_archive):
        cls.user = User.objects.create_user(
            username='admin',
            email='kvydyk@gmail.com',
            password='12345rtx',
        )

        cls.faker = Faker()
        file_name = cls.faker.file_name(extension='jpeg')
        image = cls.faker.image()
        file = ContentFile(image, name=file_name)

        cls.story = Story.objects.create(
            img=file,
            owner=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)
    
    def test_get_stories(self):
        self.story.archived = True
        self.story.save()

        response = self.client.get(reverse('blogs:archived_stories'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['stories']), 1)

    def test_create_story(self):
        file_name = self.faker.file_name(extension='jpeg')
        image = self.faker.image()
        file = ContentFile(image, name=file_name)

        response = self.client.post(reverse('blogs:create_story'), {'img': file})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.stories.count(), 2)

    def test_delete_story(self):
        url = reverse('blogs:delete_story', args=[self.story.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.stories.count(), 0)
