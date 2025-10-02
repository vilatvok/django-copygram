from django.http import JsonResponse
from django.views.generic.list import ListView
from django.views import View

from blogs.models import Post


class PostsMixin(ListView):
    template_name = 'blogs/posts.html'
    context_object_name = 'posts'
    paginate_by = 20


class PostActionMixin(View):

    def get_action_response(self, request, post_id, func):
        post = Post.objects.get(id=post_id)
        response = func(request.user, post)
        return JsonResponse({'status': response})
