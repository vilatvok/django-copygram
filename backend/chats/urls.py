from chats.views import private, groups

from common.conf import path


app_name = 'chats'


urlpatterns = [
    path('create-group/', groups.CreateGroupChatView.as_view(), 'create_group'),
    path('groups/', groups.GroupChatsView.as_view(), 'groups'),
    path('groups/<int:group_id>/', groups.GroupChatView.as_view(), 'group_chat'),
    path('groups/<int:group_id>/members/', groups.GroupChatUsersView.as_view(), 'group_users'),
    path('groups/<int:group_id>/edit-group/', groups.EditGroupView.as_view(), 'edit_group'),
    path('groups/<int:group_id>/delete-group/', groups.DeleteGroupView.as_view(), 'delete_group'),

    path('create-private/<slug:user_slug>/', private.CreatePrivateChatView.as_view(), 'create_private'),
    path('private-chats/', private.PrivateChatsView.as_view(), 'private_chats'),
    path('private-chats/<int:chat_id>/', private.PrivateChatView.as_view(), 'private_chat'),
]
