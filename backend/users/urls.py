from django.urls import reverse_lazy, include
from django.contrib.auth.views import (
    LogoutView,
    PasswordChangeView,
    PasswordResetDoneView,
    PasswordResetConfirmView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from two_factor.views.core import LoginView

from common.conf import path
from users.api import views
from users.views import accounts, actions, followers, auth


app_name = 'users'


user_urls = [
    path('', accounts.ProfileView.as_view(), 'profile'),
    path('followers/', followers.FollowersView.as_view(), 'followers'),
    path('following/', followers.FollowingView.as_view(), 'following'),
    path('follow/', followers.FollowUserView.as_view(), 'follow'),
    path('unfollow/', followers.UnfollowUserView.as_view(), 'unfollow'),
    path('block/', accounts.BlockUserView.as_view(), 'block'),
    path('unblock/', accounts.UnblockUserView.as_view(), 'unblock'),
    path('report/', actions.CreateReportView.as_view(), 'create_report'),
]


password_urls = [
    path('password-reset/',auth.PasswordResetView.as_view(), 'password_reset'),
    path('password-user-confirm/', auth.PasswordUserConfirmView.as_view(),'password_user_confirm'),
    path(
        route='password-reset/done/',
        view=PasswordResetDoneView.as_view(
            template_name="info_page.html"
        ),
        name='password_reset_done',
    ),
    path(
        route='password-reset/<uidb64>/<token>/',
        view=PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy('users:login'),
        ),
        name='password_reset_confirm',
    ),
    path(
        route='change-password/',
        view=PasswordChangeView.as_view(
            success_url=reverse_lazy('blogs:feed'),
            template_name='users/change_password.html',
        ),
        name='change_password',
    ),
]


actions_urls = [
    path('actions/', actions.ActionsView.as_view(), 'actions'),
    path('clear-actions/', actions.ClearActionsView.as_view(), 'clear_actions'),
    path('delete-action/<int:action_id>/', actions.DeleteActionView.as_view(), 'delete_action'),
]


auth_urls = [
    path('login/', LoginView.as_view(template_name="users/login.html"), 'login'),
    path('logout/', LogoutView.as_view(), 'logout'),
    path('register/', auth.RegisterView.as_view(), 'register'),
    path('register-confirm/<uidb64>/<token>/', auth.RegisterConfirmView.as_view(), 'register_confirm'),
]


api_urls = [
    path('api/settings/', views.SettingsAPIView.as_view()),
    path('api/vip-status/', views.VipAPIView.as_view()),
    path('api/token/', TokenObtainPairView.as_view(), 'token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), 'token_refresh'),
    path('api/register-confirm/<uidb64>/<token>/',views.RegisterConfirmAPIView.as_view()),
    path('api/accept-follower/<slug:user_slug>/', views.AcceptFollowerAPIView.as_view()),
    path('api/reject-follower/<slug:user_slug>/', views.RejectFollowerAPIView.as_view()),
    path('api/password-change/', views.PasswordChangeAPIView.as_view()),
    path('api/password-reset/', views.PasswordResetAPIView.as_view()),
    path('api/password-reset-confirm/<uidb64>/<token>/', views.PasswordResetConfirmAPIView.as_view()),
]


urlpatterns = [
    path('activity/', actions.ActivityView.as_view(), 'activity'),
    path('saved-posts/', actions.SavedPostsView.as_view(), 'saved_posts'),
    path('blocked/', accounts.BlockedView.as_view(), 'blocked'),
    path('search/', actions.SearchView.as_view(), 'search'),
    path('users/edit/', accounts.EditProfileView.as_view(), 'edit_profile'),
    path('users/<slug:user_slug>/', include(user_urls)),
    path('settings/', accounts.EditSettingsView.as_view(), 'edit_settings'),
    path('accept-follower/<slug:user_slug>/', followers.AcceptFollowerView.as_view(), 'accept_follower'),
    path('reject-follower/<slug:user_slug>/', followers.RejectFollowerView.as_view(), 'reject_follower'),
    path('delete-account/', accounts.DeleteProfileView.as_view(), 'delete_account'),
    path('two_fa/', auth.SetupTwoFaView.as_view(), 'enable_fa'),
    path('disable-two-fa/', auth.DisableTwoFaView.as_view(), 'disable_fa'), 
] + password_urls + actions_urls + auth_urls + api_urls
