from common import redis_client
from users.models import User


def get_actions(user: User, key: str):
    if user.is_authenticated:
        actions = redis_client.scard(key)
    else:
        actions = 0
    return actions


def unread_actions(request):
    user = request.user
    actions = get_actions(user, f'user:{user.username}:unread_actions')
    return {'unread_actions': actions}


def unread_group_messages(request):
    user = request.user
    messages = get_actions(user, f'user:{user.username}:group_unread')
    return {'unread_group_messages': messages}


def unread_chat_messages(request):
    user = request.user
    messages = get_actions(user, f'user:{user.username}:private_unread')
    return {'unread_chat_messages': messages}
