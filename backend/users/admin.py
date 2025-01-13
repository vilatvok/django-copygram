from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users import models


@admin.register(models.User)
class CustomUserAdmin(UserAdmin):
    list_display = ['id', 'username', 'email', 'is_superuser', 'referral_code']
    fieldsets = (
        (None, {'fields': ('slug', 'username', 'password')}),
        (
            ('Personal info'),
            {'fields': (
                'first_name',
                'last_name',
                'email',
                'avatar',
                'bio',
                'gender',
            )},
        ),
        (
            ('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            ('Important dates'),
            {'fields': (
                'date_joined',
                'last_login',
                'last_activity',
                'last_name_change',
                'is_online',
            )}
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("slug", "username", "email", "password1", "password2"),
            },
        ),
    )
    prepopulated_fields = {'slug': ['username']}
    ordering = ['id']


@admin.register(models.Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('id', 'referrer', 'referred_by', 'created_at')
    search_fields = ('referrer__username', 'referred_by__username')


@admin.register(models.Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'owner',
        'created_at',
        'act',
        'object_id',
        'file',
    )
    list_filter = ('created_at',)
    autocomplete_fields = ('owner',)
    search_fields = ('owner__username',)


@admin.register(models.Follower)
class FollowerAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user')
    search_fields = ('from_user__username', 'to_user__username')

    # def has_add_permission(self, request):
    #     return False
    
    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(models.Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user')
    search_fields = ('from_user__username', 'to_user__username')


@admin.register(models.Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_from', 'report_on', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('report_from__username', 'report_on__username')


@admin.register(models.UserPrivacy)
class UserPrivacyAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'private_account',
        'comments',
        'likes',
        'online_status',
    )
    list_editable = ('private_account', 'comments', 'likes', 'online_status')
    list_filter = ('private_account', 'comments', 'likes', 'online_status')
    search_fields = ('user__username', 'user__email')


@admin.register(models.UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'login_time', 'logout_time', 'session_time')
    list_filter = ('login_time', 'logout_time')
    search_fields = ('user__username', 'user__email')
    ordering = ['-login_time']


@admin.register(models.UserDayActivity)
class UserDayActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'total_activity')
    list_filter = ('date',)
    search_fields = ('user__username', 'user__email')
    ordering = ['-date']
