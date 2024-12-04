import random
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from users.models import User
from blogs.models import Post, Comment


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--count', dest='count', type=int)

    def handle(self, *args, **options):
        fake = Faker()
        count = options['count']
        users = User.objects.all()
        posts = Post.objects.all()
        comments = []
        try:
            for _ in range(count):
                try:
                    user = random.choice(users)
                    post = random.choice(posts)
                except IndexError:
                    self.stderr.write('Please provide more users and posts!')
                    return
                c = Comment(owner=user, post=post, text=fake.text())
                comments.append(c)
            Comment.objects.bulk_create(comments)
            self.stdout.write(f'{count} comments generated!')
        except TypeError:
            self.stderr.write('Please provide a count of comments to generate!')
