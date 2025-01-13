import secrets

from datetime import timedelta, datetime, time
from django.db import models, transaction
from django.db.models.fields.generated import GeneratedField
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation,
)
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from common.models import BaseModel
from users.managers import CustomUserManager
from users.validators import UsernameValidator


class User(AbstractUser):
    """Override default user model."""

    GENDER = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    username_validator = UsernameValidator()
    username = models.CharField(
        verbose_name="username",
        max_length=150,
        unique=True,
        help_text=(
            "Required. 150 characters or fewer. Letters, digits and ./_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": "A user with that username already exists.",
        },
    )
    slug = models.SlugField(unique=True, max_length=255)
    avatar = models.ImageField(upload_to='users/%Y/%m/%d/', blank=True)
    email = models.EmailField(unique=True)
    is_online = models.BooleanField(default='False')
    actions = GenericRelation(to='Action', related_query_name='user')
    bio = models.TextField(blank=True)
    gender = models.CharField(choices=GENDER, max_length=6, default='male')
    referral_code = models.CharField(max_length=32, unique=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    last_name_change = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(
        _("active"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    objects = CustomUserManager()

    class Meta:
        indexes = [
            models.Index(fields=['username'])
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__username = self.username

    def get_absolute_url(self):
        return reverse("users:profile", kwargs={"user_slug": self.slug})

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.username)
            self.referral_code = secrets.token_urlsafe(24)
        else:
            if self.__username != self.username:
                self.slug = slugify(self.username)
                last_change = self.last_name_change
                if last_change:
                    allow_to_change = last_change + timedelta(weeks=1)
                    diff = timezone.now() > allow_to_change
                    if diff:
                        self.last_name_change = timezone.now()
                    else:
                        days_left = (allow_to_change - timezone.now()).days
                        msg = f"You can change username after {days_left} days."
                        raise ValidationError(msg)
                else:
                    self.last_name_change = timezone.now()
        super().save(*args, **kwargs)


class UserPrivacy(models.Model):
    USER_CHOICES = [
        ('everyone', 'Everyone'),
        ('followers', 'Followers'),
        ('nobody', 'Nobody'),
    ]

    user = models.OneToOneField(
        to='users.User',
        primary_key=True,
        on_delete=models.CASCADE,
        related_name='privacy',
    )
    private_account = models.BooleanField(default=False)
    likes = models.CharField(
        choices=USER_CHOICES,
        max_length=10,
        default='everyone',
    )
    comments = models.CharField(
        choices=USER_CHOICES,
        max_length=10,
        default='everyone',
    )
    online_status = models.CharField(
        choices=USER_CHOICES,
        max_length=10,
        default='everyone',
    )

    class Meta:
        verbose_name_plural = 'Users privacy'


class UserActivity(models.Model):
    user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='activities',
    )
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(blank=True, null=True)
    session_time = GeneratedField(
        expression=models.F('logout_time') - models.F('login_time'),
        output_field=models.DurationField(),
        db_persist=True,
    )

    class Meta:
        verbose_name_plural = 'User activities'


class UserDayActivity(models.Model):
    user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='day_activities',
    )
    date = models.DateField(auto_now_add=True)
    total_activity = models.DurationField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='unique_day_activity',
            ),
        ]
        verbose_name_plural = 'User day activities' 

    def get_day_activities(self):
        return self.user.activities.filter(login_time__date=self.date)
    
    def get_total_day_activity(self):
        today = timezone.now().date()
        logs = UserActivity.objects.filter(user=self.user, login_time__date=today)
        total_activity = timedelta()
        for log in logs:
            if not log.logout_time:
                continue

            # Truncate date in case of login/logout time is not today
            elif log.login_time.date() != today:
                start_of_day = datetime.combine(today, time.min)
                total_activity += log.logout_time - start_of_day
            elif log.logout_time.date() != today:
                end_of_day = datetime.combine(today, time.max)
                total_activity += end_of_day - log.login_time
            else:
                total_activity += log.session_time
        return total_activity

    def save(self, *args, **kwargs):
        self.total_activity = self.get_total_day_activity()
        super().save(*args, **kwargs)


class Referral(BaseModel):
    referrer = models.ForeignKey(
        to='users.User',
        related_name='referrals',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    referred_by = models.OneToOneField(
        to='users.User',
        related_name='referred_by',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return f'{self.referrer.username} invited {self.referrer_by.username}'


class Action(BaseModel):
    """
    Model for all posible actions in project.
    Contains a generic foreign key to pair with each model.
    """

    owner = models.ForeignKey(
        to='users.User',
        related_name='actions',
        on_delete=models.CASCADE,
    )
    act = models.CharField(max_length=255)
    file = models.FileField()
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('post', 'comment', 'user')}
    )
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f'{self.owner} {self.act}'


class Follower(models.Model):
    from_user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='following',
    )
    to_user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='followers',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='unique_followers',
            ),
            models.CheckConstraint(
                check=~models.Q(from_user=models.F('to_user')),
                name='self_following',
            )
        ]

    def __str__(self):
        return f'{self.from_user} followed {self.to_user}'


class Block(models.Model):
    from_user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='blocked',
    )
    to_user = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='blocked_by',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='unique_blocking',
            ),
             models.CheckConstraint(
                check=~models.Q(from_user=models.F('to_user')),
                name='self_blocking',
            )
        ]

    def __str__(self):
        return f'{self.from_user} blocked {self.to_user}'


class Report(BaseModel):
    report_from = models.ForeignKey(
        to='users.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reports',
    )
    report_on = models.ForeignKey(
        to='users.User',
        on_delete=models.CASCADE,
        related_name='reports_by',
    )
    reason = models.TextField()

    def __str__(self):
        return f'{self.report_from} report on {self.report_on}'
