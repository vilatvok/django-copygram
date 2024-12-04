from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.cache import cache

from common.utils import create_action
from users import models
from users.tasks import delete_account_scheduler
from users.utils import recommend_users


@receiver(user_logged_in, sender=models.User)
def set_online_status(user, **kwargs):
    user.is_online = True
    user.save()
    models.UserActivity.objects.create(user=user)


@receiver(user_logged_out, sender=models.User)
def set_offline_status(user, **kwargs):
    # create session time log on exit
    models.UserActivity.objects.filter(
        user=user,
        logout_time=None,
    ).update(logout_time=timezone.now())

    # create or update daily activity log
    obj, created = models.UserDayActivity.objects.get_or_create(
        user=user,
        date=timezone.now().date(),
    )
    if not created:
        # * Method save contains logic for updating
        obj.save()

    user.is_online = False
    user.save()


@receiver(post_save, sender=models.User)
def create_user_privacy(instance, created, **kwargs):
    if created:
        models.UserPrivacy.objects.create(user_id=instance.id)
        delete_account_scheduler(instance.id)


@receiver([post_save, post_delete], sender=models.Block)
def cache_blocked(**kwargs):
    cache.delete_many(['blocked', 'blocked_by', 'blocked_from'])


@receiver([post_save], sender=models.Follower)
def post_follow(instance, created, **kwargs):
    if created:
        create_action(instance.from_user, 'followed you', instance.to_user)
        recommend_users(instance.from_user)


@receiver(post_delete, sender=models.Follower)
def post_unfollow(instance, **kwargs):
    recommend_users(instance.from_user)
