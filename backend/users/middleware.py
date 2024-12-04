from django.http import Http404
from django.shortcuts import redirect
from django.conf import settings


class LoginRequiredMiddleware:
    """Require login from all templates views."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed_domens = [
            request.path.startswith('/login'),
            request.path.startswith('/feed'),
            request.path.startswith('/api'),
            request.path.startswith('/social'),
            request.path.startswith('/password'),
            request.path.startswith('/register'),
            request.path.startswith('/swagger'),
            request.path.startswith('/__debug__'),
            request.path.startswith(settings.MEDIA_URL),
        ]
        if not request.user.is_authenticated and not any(allowed_domens):
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)


class AnonymousRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        domens = [
            request.path.startswith('/login'),
            request.path.startswith('/password'),
            request.path.startswith('/register'),
        ]

        if request.user.is_authenticated and any(domens):
            raise Http404('You can\'t visit this page, you\'re already logged in.')
        return self.get_response(request)
