def user_changed(sender, instance, **kwargs):
    # import is written inside function to avoid circular dependency
    from accounts.services import UserService
    UserService.invalidate_user(instance.id)


def profile_changed(sender, instance, **kwargs):
    from accounts.services import UserService
    UserService.invalidate_profile(instance.user_id)
