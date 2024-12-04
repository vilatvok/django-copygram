from io import BytesIO
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from django.utils import timezone
from django.db import models, transaction
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericRelation
from django.core.files.base import ContentFile
from tree_queries.models import TreeNode
from taggit.managers import TaggableManager

from blogs.managers import CommentQuerySet, PostManager
from common.models import BaseModel


class BaseMedia(BaseModel):
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_archived = self.archived


class Post(BaseMedia):
    owner = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='posts')
    description = models.TextField(blank=True)
    likes = models.ManyToManyField('users.User', related_name='likes', blank=True)
    saved = models.ManyToManyField('users.User', related_name='saved', blank=True)
    is_comment = models.BooleanField(default=True)
    actions = GenericRelation('users.Action', related_query_name='post')
    archived = models.BooleanField(default=False)
    tags = TaggableManager(blank=True)

    objects = PostManager()

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            self.owner.last_activity = timezone.now()
            self.owner.save()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blogs:post', kwargs={'post_id': self.pk})

    def get_files(self):
        return self.files.select_related('post')

    def get_tags(self):
        return self.tags.all()


# Post -> PostMedia
class PostMedia(models.Model):
    post = models.ForeignKey(
        to='blogs.Post',
        related_name='files',
        on_delete=models.CASCADE,
    )
    file = models.FileField(upload_to='posts/%Y/%m/%d/')

    class Meta:
        verbose_name_plural = 'Posts media'

    def process_image(self):
        if not self.pk:
            try:
                img = Image.open(self.file)
            except UnidentifiedImageError:
                pass
            else:
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                size = (350, 225)
                img = img.resize(size, Image.LANCZOS)

                temp_img = BytesIO()
                img.save(temp_img, format='JPEG', optimize=True, quality=100)
                temp_img.seek(0)

                img_name = f"{uuid4()}.jpg"
                self.file.save(
                    name=img_name,
                    content=ContentFile(temp_img.read()),
                    save=False,
                )

    @classmethod
    def bulk_create_with_processing(cls, objs):
        # Process images for each object
        for obj in objs:
            obj.process_image()

        # Bulk create the objects
        cls.objects.bulk_create(objs)

    def save(self, *args, **kwargs):
        self.process_image()
        super().save(*args, **kwargs)


# Post -> Comment
class Comment(TreeNode, BaseModel):
    owner = models.ForeignKey(
        to='users.User',
        related_name='comments',
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        to='blogs.Post',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    parent = models.ForeignKey(
        to='self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='replies',
    )
    likes = models.ManyToManyField(
        to='users.User',
        related_name='comment_likes',
        blank=True,
    )
    text = models.CharField(max_length=255)

    objects = CommentQuerySet.as_manager()


class UninterestingPost(models.Model):
    user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='uninteresting_posts'
    )
    post = models.ForeignKey(
        to='blogs.Post',
        on_delete=models.CASCADE,
        related_name='uninteresting_by'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                name='unique_uninteresting_post',
            ),
        ]

    def __str__(self):
        return f'{self.user} not interested in {self.post}'


class Story(BaseMedia):
    owner = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='stories',
    )
    img = models.ImageField(upload_to='stories/%Y/%m/%d/')
    archived = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Stories'

    @transaction.atomic
    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)
