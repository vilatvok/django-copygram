import json
import pandas as pd

from datetime import timedelta
from celery import shared_task
from celery.result import allow_join_result
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from common import redis_client
from blogs.models import Story
from blogs.similarities import Recognizer


@shared_task
def archive_story(story_id):
    """
    Remove story after 24 hours.
    """

    story = Story.objects.get(id=story_id)
    story.archived = True
    story.save()


def archive_story_scheduler(story_id, story_date):
    date = story_date + timedelta(days=1)
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=date.minute,
        hour=date.hour,
        day_of_month=date.day,
        month_of_year=date.month,
    )
    PeriodicTask.objects.create(
        crontab=crontab,
        name=f'archive-story-{story_id}',
        task='blogs.tasks.archive_story',
        args=json.dumps([story_id]),
        one_off=True,
    )


@shared_task
def remove_similar_posts(username: str, data: list[dict], posts: list[dict]):
    exclude = update_posts_recommendations.delay(data, posts)
    with allow_join_result():
        exclude = set(exclude.get())
        if len(exclude):
            redis_client.srem(f'user:{username}:posts_recommendations', *exclude)


@shared_task
def update_posts_recommendations(uninteresting: list[dict], others: list[dict]):
    """Find similar posts, based on images and descriptions."""

    posts = []
    image_data = pd.read_hdf('media/images_similarities.h5', 'data')
    for un in uninteresting:
        image = un['file'].split('/')[-1].split('.')[0]
        description = un['description']
        for post in others:
            another_image = post['file'].split('/')[-1].split('.')[0]
            another_description = post['description']

            # get similarity between images
            try:
                sim_images = image_data.at[image, another_image]
            except KeyError:
                sim_images = 0

            if description and another_description:
                sim_texts = Recognizer.compare_descriptions(
                    description,
                    another_description,
                )
            else:
                sim_texts = 0

            if sim_images > 0.75 or sim_texts > 0.75:
                posts.append(post['id'])
    return posts
