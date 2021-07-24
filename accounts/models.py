from accounts.listeners import user_changed, profile_changed
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_delete, post_save

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
    # put import inside the function to avoid circular dependency
    from accounts.services import UserService

    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    profile, _ = UserService.get_profile_through_cache()
    # use the attribute of user object to cache
    # to avoid multiple times of querying the same user profile (duplicate db query)
    setattr(user, 'cached_user_profile', profile)
    return profile


# added a profile property to User Model for fast querying
User.profile = property(get_profile)

# hook up with listener to invalidate cache
pre_delete.connect(user_changed, sender=User)
post_save.connect(user_changed, sender=User)

pre_delete.connect(profile_changed, sender=UserProfile)
post_save.connect(profile_changed, sender=UserProfile)

