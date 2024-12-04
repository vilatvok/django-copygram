from django.http import JsonResponse
from django.views.generic.list import ListView
from django.views import View
from django.core.files.storage import default_storage

from blogs.models import Post
from blogs.filters import PostFilter


class PostsMixin(ListView):
    template_name = 'blogs/posts.html'
    context_object_name = 'posts'
    paginate_by = 20

    def get_queryset(self):
        queryset = self.perform_queryset()
        self.filter_queryset = PostFilter(self.request.GET, queryset=queryset)

        processed_queryset = []
        for post in self.filter_queryset.qs:
            # Ensure `file` is resolved via `default_storage.url` if it exists
            post.file = default_storage.url(post.file) if post.file else None
            processed_queryset.append(post)

        return processed_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.filter_queryset.form
        return context

    def perform_queryset(self):
        raise NotImplementedError


class PostActionMixin(View):
    def get_action_response(self, request, post_id, func):
        post = Post.objects.get(id=post_id)
        response = func(request.user, post)
        return JsonResponse({'status': response})
