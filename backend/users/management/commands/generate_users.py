from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from users.models import User


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--count', dest='count', type=int)

    def handle(self, *args, **options) -> str | None:
        fake = Faker()
        count = options['count']
        try:
            for _ in range(count):
                User.objects.create(
                    username=fake.user_name(),
                    email=fake.email(),
                    password=fake.password(),
                )
            self.stdout.write(f'{count} users generated!')
        except TypeError:
            self.stderr.write('Please provide a count of users to generate!')
