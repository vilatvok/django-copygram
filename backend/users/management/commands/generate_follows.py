import random

from django.core.management.base import BaseCommand, CommandParser
from django.db.utils import IntegrityError

from users.models import Follower, User


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--count', dest='count', type=int)

    def handle(self, *args, **options) -> str | None:
        count = options['count']
        all_users = User.objects.all()
        try:
            for _ in range(count):
                choices = random.sample(list(all_users), 2)
                try:
                    Follower.objects.create(
                        from_user=choices[0],
                        to_user=choices[1],
                    )
                except IntegrityError:
                    continue
            self.stdout.write(f'{count} follows generated!')
        except TypeError:
            self.stderr.write('Please provide a count of users to generate!')
