from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

from common.utils import create_action, get_blocked_users, redis_client
from users.models import User, Action, Follower, Block
from users.tasks import generate_recommendations
from blogs.models import Comment, Post


def get_users(user: User):
    blocked_users = get_blocked_users(user)
    queryset = (
        User.objects.annotated(current_user=user).
        exclude(id__in=blocked_users)
    )
    return queryset


def get_user_posts(user_id: int):
    posts = Post.objects.annotated().filter(owner=user_id)
    return posts


def recommend_users(user: User) -> None:
    users = [user.id]
    followers = user.followers.select_related('from_user')
    for follower in followers:
        users.append(follower.from_user.id)
    generate_recommendations.delay(users)

    # * For debugging
    # generate_recommendations(users)


def generate_reset_password_params(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.id))
    token = default_token_generator.make_token(user)
    return uidb64, token


def send_reset_email(user: User, link: str, ref=None) -> None:
    uidb64, token = generate_reset_password_params(user)
    if 'register' in link:
        subject = 'Confirm registration'
        if ref:
            message = (
                'Click here to confirm registration:\n'
                f'{link}/{uidb64}/{token}/?ref={ref}'
            )
        else:
            message = (
                'Click here to confirm registration:\n'
                f'{link}/{uidb64}/{token}/'
            )
    else:
        subject = 'Reset password'
        message = (
            'Click here to reset password:\n'
            f'{link}/{uidb64}/{token}/'
        )

    send_mail(
        subject=subject,
        message=message,
        from_email='kvydyk@gmail.com',
        recipient_list=[user.email],
    )


def check_token(uidb64, token) -> tuple:
    uid = force_str(urlsafe_base64_decode(uidb64))
    user = User.objects.get(id=uid)
    is_valid = default_token_generator.check_token(user, token)
    return (user, is_valid)


def follow_user(from_user: User, to_user: User) -> str:
    is_followed = Follower.objects.filter(from_user=from_user, to_user=to_user)
    if not is_followed.exists():
        # If user has private account then send follow request
        if to_user.privacy.private_account:
            key = f'user:{to_user.username}:requests'
            if redis_client.sismember(key, from_user.username):
                redis_client.srem(key, from_user.username)
                return 'Canceled'
            else:
                redis_client.sadd(key, from_user.username)
                create_action(from_user, 'wants to follow you', to_user)
                return 'Request was sent'
        else:
            with transaction.atomic():
                Follower.objects.create(from_user=from_user, to_user=to_user)
                create_action(from_user, 'followed you', to_user)
            return 'Followed'
    return 'Already followed'


def unfollow_user(from_user_id: int, to_user_id: int) -> str:
    is_followed = Follower.objects.filter(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
    )
    if is_followed.exists():
        is_followed.delete()
        return 'Unfollowed'
    return 'Not followed'


def block_user(from_user: User, to_user: User) -> str:
    is_blocked = Block.objects.filter(from_user=from_user, to_user=to_user)
    if not is_blocked.exists():
        with transaction.atomic():
            Block.objects.create(from_user=from_user, to_user=to_user)

            posts = from_user.likes.filter(owner=to_user)
            user_posts = to_user.likes.filter(owner=from_user)

            for post in posts:
                post.likes.remove(from_user)
            for post in user_posts:
                post.likes.remove(to_user)

            Comment.objects.filter(
                Q(owner=to_user, post__owner=from_user) |
                Q(owner=from_user, post__owner=to_user)
            ).delete()

            Follower.objects.filter(
                Q(from_user=to_user, to_user=from_user) |
                Q(from_user=from_user, to_user=to_user)
            ).delete()

            Action.objects.filter(
                Q(owner=to_user, post__owner=from_user) |
                Q(owner=to_user, user=from_user) |
                Q(owner=from_user, post__owner=to_user) |
                Q(owner=from_user, user=to_user)
            ).delete()
            return 'Blocked'
    return 'Already blocked'


def unblock_user(from_user_id: int, to_user_id: int) -> str:
    is_blocked = Block.objects.filter(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
    )
    if is_blocked.exists():
        is_blocked.delete()
        return 'Unblocked'
    return 'Not blocked'


def process_follower_request(from_user_slug: str, to_user: User, act: str) -> str:
    from_user = User.objects.get(slug=from_user_slug)
    key = f'user:{to_user.username}:requests'
    request_exists = redis_client.smembers(key)
    if from_user.username not in request_exists:
        msg = f'There is no request from {from_user.username}'
        return msg
    else:
        with transaction.atomic():
            if act == 'accept':
                response = 'Accepted'
                Follower.objects.create(from_user=from_user, to_user=to_user)
            elif act == 'reject':
                response = 'Rejected'
            Action.objects.filter(
                owner=from_user,
                user=to_user,
                act='wants to follow you',
            ).delete()
        redis_client.srem(key, from_user.username)
        return response
