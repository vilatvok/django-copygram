import json

from datetime import timedelta, datetime
from celery import shared_task
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from common import redis_client
from users.recommendations import Recommender
from users.models import User


@shared_task
def cancel_vip(username: str):
    redis_client.srem('active_vip_users', username)


def cancel_vip_scheduler(username: str, duration: int):
    date = datetime.now() + timedelta(minutes=duration)
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=date.minute,
        hour=date.hour,
        day_of_month=date.day,
        month_of_year=date.month,
    )
    PeriodicTask.objects.create(
        crontab=crontab,
        name=f'cancel-vip-{username}-',
        task='users.tasks.cancel_vip',
        args=json.dumps([username]),
        one_off=True,
    )


@shared_task
def delete_account(user_id: int):
    user = User.objects.get(id=user_id)
    user.delete()


def delete_account_scheduler(user_id: int):
    date = datetime.now() + timedelta(hours=6)
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=date.minute,
        hour=date.hour,
        day_of_month=date.day,
        month_of_year=date.month,
    )
    PeriodicTask.objects.create(
        crontab=crontab,
        name=f'delete-user-{user_id}',
        task='users.tasks.delete_account',
        args=json.dumps([user_id]),
        one_off=True,
    )


@shared_task(bind=True, max_retries=10)
def generate_recommendations(self, users: list[int]):
    # * Use lock to prevent multiple tasks from running simultaneously
    # * It is important to release the lock after the task is completed 

    users = User.objects.filter(id__in=users)
    lock = redis_client.lock("single_task_lock", timeout=60)
    if lock.acquire(blocking=False):
        try:
            for user in users:
                recommender = Recommender(user)
                recommender.generate_recommendations()
        finally:
            lock.release()
    else:
        self.retry(countdown=5)
