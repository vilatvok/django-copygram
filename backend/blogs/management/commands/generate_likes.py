import random

from django.db.models import Model
from django.core.management.base import BaseCommand, CommandParser

from users.models import User
from blogs.models import Post


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--count', dest='count', type=int)

    def handle(self, *args, **options):
        count = options['count']
        users = User.objects.all()
        posts = Post.objects.all()

        ThroughModel: Model = Post.likes.through

        likes = []
        try:
            for _ in range(count):
                try:
                    user = random.choice(users)
                    post = random.choice(posts)
                except IndexError:
                    self.stderr.write('Please provide more users and posts!')
                    return
                like = ThroughModel(post_id=post.id, user_id=user.id)
                likes.append(like)
            ThroughModel.objects.bulk_create(likes, ignore_conflicts=True)
            self.stdout.write(f'{count} likes generated!')
        except TypeError:
            self.stderr.write('Please provide a count of likes to generate!')
