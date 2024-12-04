from django.urls import include

from common.conf import path
from blogs.views import posts, archive, stories


app_name = 'blogs'


post_urls = [
    path('', posts.PostView.as_view(), 'post'),
    path('edit/', posts.EditPostView.as_view(), 'edit_post'),
    path('like/', posts.LikePostView.as_view(), 'add_like'),
    path('save/', posts.SavePostView.as_view(), 'save_post'),
    path('unlike/', posts.UnlikePostView.as_view(), 'remove_like'),
    path('unsave/', posts.UnsavePostView.as_view(), 'unsave_post'),
    path('delete/', posts.DeletePostView.as_view(), 'delete_post'),
    path('likes/', posts.PostLikesView.as_view(), 'post_likes'),
    path('archive/', archive.ArchivePostView.as_view(), 'archive_post'),
    path('comment/', posts.CommentOnView.as_view(), 'add_comment'),
    path('delete-comment/<int:comment_id>/', posts.DeleteCommentView.as_view(), 'delete_comment'),
    path('add-uninteresting/', posts.AddUninterestingPostView.as_view(), 'add_uninteresting'),
    path('remove-uninteresting/', posts.RemoveUninterestingPostView.as_view(), 'remove_uninteresting'),
]


posts_urls = [
    path('<int:post_id>/', include(post_urls)),
    path('create/', posts.CreatePostView.as_view(), 'create_post'),
    path('tags/<slug:tag_slug>/posts/', posts.TagPostsView.as_view(), 'tag_posts'),
]


archive_urls = [
    path('stories/', archive.ArchivedStoriesView.as_view(), 'archived_stories'),
    path('posts/', archive.ArchivedPostsView.as_view(), 'archived_posts'),
    path('posts/<int:post_id>/', archive.ArchivedPostView.as_view(), 'archived_post'),
    path('posts/<int:post_id>/restore/', archive.RestorePostView.as_view(), 'restore_post'),
]


stories_urls = [
    path('create-story/', stories.CreateStoryView.as_view(), 'create_story'),
    path('delete-story/<int:story_id>/', stories.DeleteStoryView.as_view(), 'delete_story'),
]


urlpatterns = [
    path('', posts.FeedView.as_view(), 'feed'),
    path('explore/', posts.ExploreView.as_view(), 'explore'),
    path('uninteresting-posts/', posts.UninterestingPostsView.as_view(), 'uninteresting_posts'),
    path('posts/', include(posts_urls)),
    path('stories/', include(stories_urls)),
    path('archive/', include(archive_urls)),
]
