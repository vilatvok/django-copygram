from django.contrib.auth.models import Group


USER_FIELDS = ["username", "email"]


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        return {"is_new": False}

    fields = {
        name: kwargs.get(name, details.get(name))
        for name in backend.setting("USER_FIELDS", USER_FIELDS)
    }
    if not fields:
        return

    fields['is_active'] = True
    return {"is_new": True, "user": strategy.create_user(**fields)}


def add_user_to_group(backend, user, response, *args, **kwargs):
    """
    The user, who was logged in through social,
    is forbidden to change the password.
    """
    group = Group.objects.get(name='social')
    if group:
        user.groups.add(group)
