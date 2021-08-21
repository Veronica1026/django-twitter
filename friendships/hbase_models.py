from django_hbase import models


class HBaseFollowing(models.HBaseModel):
    """
    stores the people that from_user_id follows, row_key is sorted using from_user_id + created_at
    queries supported:
    - all the people A follows, sorted by time
    - all the people A follows within a time frame
    - the first X people that A follows before/after a specific time
    """
    # row key
    # reverse = True is used to avoid hot keys, can be used for fields that do not need range query
    from_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()

    # column key
    to_user_id = models.IntegerField(column_family='cf')

    class Meta:
        table_name = 'twitter_followings'
        row_key= ('from_user_id', 'created_at')


class HBaseFollower(models.HBaseModel):
    """
    stores the people that are following to_user_id, sorted using to_user_id and created_at
    queries supported:
    - all the followers that A has sorted by time
    - all the people that followed A in a time frame
    - the first X people that followed A before/after a specific time
    """

    # row key
    to_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    # column key
    # we give it a column family name so it's easier to tell which field is used fo column key, and which is for row key
    from_user_id = models.IntegerField(column_family='cf')

    class Meta:
        row_key = ('to_user_id', 'created_at')
        table_name = 'twitter_followers'
