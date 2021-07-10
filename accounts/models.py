from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    # one to one field will create a unique index, to avoid multiple user profiles pointing to the same user
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    avatar = models.FileField(null=True)

    nickname = models.CharField(null=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} {}'.format(self.user, self.nickname)


def get_profile(user):
    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    # use the attribute of user object to cache
    # to avoid multiple times of querying the same user profile (duplicate db query)
    setattr(user, 'cached_user_profile', profile)
    return profile


# added a profile property to User Model for fast querying
User.profile = property(get_profile)
