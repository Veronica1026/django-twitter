from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_delete
from likes.models import Like
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from tweets.listeners import push_tweet_to_cache
from utils.listeners import invalidate_object_cache
from utils.memcached_helper import MemcachedHelper
from utils.time_helpers import utc_now

class Tweet(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    # for newly added field, we must set null=True,
    # otherwise default=0 will loop through all the table and set the value
    # which will slow down the whole process of migration,
    # locking the table, so users cannot create new tweets at this time
    # however we can write a script to back fill the value for those old data after the migration is done
    likes_count = models.IntegerField(default=0, null=True)
    comments_count = models.IntegerField(default=0, null=True)

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at')

    def __str__(self):
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def hours_to_now(self):
        # datetime.now has no information regarding timezone. We need to convert to UTC
        return (utc_now() - self.created_at).seconds // 3600

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)


class TweetPhoto(models.Model):
    # the photo is within which tweet
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # who uploaded this photo. Although we can check user through tweet field
    # this accelerates the query of all the photos a user has uploaded
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    # photo file
    file = models.FileField()
    order = models.IntegerField(default=0)

    # status of the photo, used for auditing purposes
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # soft delete, it is only marked as delete when user deletes it, will be actually deleted later
    # real deleting takes sometime, so soft deleting helps improves performance, so we make it async
    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('user', 'created_at'),
            ('has_deleted', 'created_at'),
            ('status', 'created_at'),
            ('tweet', 'order'),
        )

    def __str__(self):
        return f'{self.tweet.id}: {self.file}'


post_save.connect(invalidate_object_cache, sender=Tweet)
pre_delete.connect(invalidate_object_cache, sender=Tweet)
post_save.connect(push_tweet_to_cache, sender=Tweet)











