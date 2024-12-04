import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from users.models import User
from blogs.models import Post, PostMedia


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--count', dest='count', type=int)

    def handle(self, *args, **options):
        fake = Faker()
        count = options['count']
        users = User.objects.all()
        posts = []
        posts_media = []
        try:
            for _ in range(count):
                user = random.choice(users)
                file_extension = fake.file_name(extension='jpeg')
                file = ContentFile(fake.image(), name=file_extension)
                p = Post(owner=user)
                pm = PostMedia(post=p, file=file)
                posts.append(p)
                posts_media.append(pm)
            Post.objects.bulk_create(posts)
            PostMedia.bulk_create_with_processing(posts_media)
            self.stdout.write(f'{count} posts generated!')
        except TypeError:
            self.stderr.write('Please provide a count of posts to generate!')
