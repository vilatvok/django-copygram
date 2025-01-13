from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from common.utils import create_action, redis_client, get_blocked_users
from blogs import utils
from blogs.models import Comment, Post, PostMedia, UninterestingPost
from blogs.forms import PostForm
from blogs.mixins import PostActionMixin, PostsMixin
from users.models import Follower


class ExploreView(PostsMixin):

    def perform_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            queryset = utils.get_explore_posts(user)
        else:
            queryset = utils.get_explore_posts()
        return queryset


class FeedView(PostsMixin):

    def perform_queryset(self):
        return utils.get_feed_posts(self.request.user.id)


class PostView(DetailView):
    template_name = 'blogs/post.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        queryset = utils.get_posts(self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        current_user = self.request.user
        post = self.object

        context = super().get_context_data(**kwargs)
        context['files'] = post.get_files()
        context['tags'] = post.get_tags()

        # store post views in redis
        post_views_key = f'post:{post.id}:views'
        with redis_client.pipeline(transaction=True) as pipeline:
            if redis_client.sismember(post_views_key, current_user.username):
                pipeline.scard(post_views_key)
            else:
                viewed_posts_key = f'user:{current_user.username}:viewed_posts'
                pipeline.sadd(viewed_posts_key, post.id)
                pipeline.sadd(post_views_key, current_user.username)
                pipeline.scard(post_views_key)
            pipeline_response = pipeline.execute()
        context['total_views'] = pipeline_response[-1]

        owner_privacy = post.owner.privacy
        is_follower = Follower.objects.filter(
            from_user=current_user,
            to_user=post.owner,
        ).exists()

        context['is_follower'] = is_follower
        context['is_uninteresting'] = UninterestingPost.objects.filter(
            user=current_user,
            post=post,
        ).exists()

        # TODO: Refactor this
        if post.is_comment:
            comments = (
                post.comments.with_tree_fields().
                with_likes().
                select_related('owner', 'post', 'parent')
            )
            context['comments'] = comments
        else:
            context['comments'] = None
        if current_user != post.owner:
            # check if user hid comments
            if post.is_comment:
                if owner_privacy.comments == 'followers':
                    context['show_comments'] = is_follower
                else:
                    context['show_comments'] = True

            # check if user hid likes count
            if owner_privacy.likes == 'followers':
                context['show_likes'] = is_follower
            elif owner_privacy.likes == 'nobody':
                context['show_likes'] = False
            else:
                context['show_likes'] = True
        else:
            if post.is_comment:
                context['show_comments'] = True
            context['show_likes'] = True
        return context


class PostLikesView(ListView):
    template_name = 'users/followers.html'
    context_object_name = 'users'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        user = self.request.user
        post = get_object_or_404(Post, id=self.kwargs['post_id'])
        blocked_users = get_blocked_users(user)
        qs = (
            post.likes.annotated(current_user=user).
            exclude(id__in=blocked_users)
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        authenticated_user = self.request.user
        requests = []
        for user in context['users']:
            key = f'user:{user.username}:requests'
            user_requests = redis_client.smembers(key)
            if authenticated_user.username in user_requests:
                requests.append(user.id)

        context['user_requests'] = requests
        return context


class CreatePostView(CreateView):
    form_class = PostForm
    template_name = 'blogs/create_post.html'

    def form_valid(self, form):
        request = self.request
        images = request.FILES.getlist('files')
        if len(images) == 0:
            form.add_error(None, "At least one image is required.")
            return self.form_invalid(form)

        with transaction.atomic():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            files = []
            for img in images:
                files.append(PostMedia(post=obj, file=img))
            PostMedia.bulk_create_with_processing(files)
        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user
        return user.get_absolute_url()


class EditPostView(UpdateView):
    queryset = Post.objects.select_related('owner')
    form_class = PostForm
    template_name = 'blogs/edit_post.html'
    pk_url_kwarg = 'post_id'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.user != self.object.owner:
            raise PermissionDenied('You cant edit this post')
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class DeletePostView(DeleteView):
    model = Post
    template_name = 'blogs/post.html'
    success_url = reverse_lazy('blogs:feed')
    pk_url_kwarg = 'post_id'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.user != self.object.owner:
            raise PermissionDenied('You cant delete this post')
        return response


class SavePostView(PostActionMixin):

    def post(self, request, post_id):
        return self.get_action_response(request, post_id, utils.save_post)


class UnsavePostView(PostActionMixin):

    def delete(self, request, post_id):
        return self.get_action_response(request, post_id, utils.unsave_post)


class LikePostView(PostActionMixin):

    def post(self, request, post_id):
        return self.get_action_response(request, post_id, utils.like_post)


class UnlikePostView(PostActionMixin):

    def delete(self, request, post_id):
        return self.get_action_response(request, post_id, utils.unlike_post)


class CommentOnView(View):

    def post(self, request, post_id):
        user = request.user
        post = Post.objects.annotated().get(id=post_id)
        text = request.POST.get('q')
        with transaction.atomic():
            Comment.objects.create(owner=user, post_id=post.id, text=text)
            if user != post.owner:
                create_action(user, 'commented on', post, post.file)
        return redirect('blogs:post', post_id)


class DeleteCommentView(View):

    def delete(self, request, post_id, comment_id):
        post = Post.objects.get(id=post_id)
        comment = Comment.objects.get(id=comment_id)
        if comment.owner != request.user and post.owner != request.user:
            return JsonResponse({'status': 'You cant delete this comment'})
        else:
            comment.delete()
            return JsonResponse({'status': 'Deleted'})


class TagPostsView(ListView):
    template_name = 'blogs/posts.html'
    context_object_name = 'posts'
    slug_url_kwarg = 'tag_slug'

    def get_queryset(self):
        qs = (
            Post.objects.annotated().
            filter(tags__name__in=[self.kwargs['tag_slug']])
        )
        return qs


class AddUninterestingPostView(View):

    def post(self, request, post_id):
        user = request.user
        UninterestingPost.objects.create(user=user, post_id=post_id)
        return redirect('blogs:explore')


class RemoveUninterestingPostView(View):

    def post(self, request, post_id):
        user = request.user
        un_post = UninterestingPost.objects.filter(user=user, post_id=post_id)
        if un_post.exists():
            un_post.delete()
        return redirect('blogs:uninteresting_posts')


class UninterestingPostsView(ListView):
    template_name = 'blogs/posts.html'
    context_object_name = 'posts'

    def get_queryset(self):
        return utils.get_uninteresting_posts(self.request.user.id)
