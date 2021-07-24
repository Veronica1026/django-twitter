def friendship_changed(sender, instance, **kwargs):
    # put import inside function to avoid circular dependency
    from friendships.services import FriendshipService
    FriendshipService.invalidate_following_cache(instance.from_user_id)
