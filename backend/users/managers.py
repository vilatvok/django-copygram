from typing import Any
from django.db import models
from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):

    def blocked(self, user):
        return self.get_queryset().filter(blocked_by__from_user=user)

    def annotated(self, current_user):
        from users.models import Follower
        from chats.models import PrivateChat

        second_user = models.OuterRef('pk')
        is_followed = Follower.objects.filter(
            from_user=current_user,
            to_user=second_user,
        )
        is_chat = PrivateChat.objects.filter(
            users=current_user,
        ).filter(users=second_user)

        users = self.annotate(
            followers_count=models.Count('followers', distinct=True),
            following_count=models.Count('following', distinct=True),
            is_followed=models.Exists(is_followed),
            is_chat=models.Exists(is_chat),
        )
        return users

    def create_superuser(
        self,
        username: str,
        email: str | None,
        password: str | None,
        **extra_fields: Any
    ) -> Any:
        extra_fields.setdefault('is_active', True)
        return super().create_superuser(username, email, password, **extra_fields)
