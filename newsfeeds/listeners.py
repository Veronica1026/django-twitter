def push_newsfeeds_to_cache(sender, instance, created, **kwargs):
    if not created:
        return

    from newsfeeds.services import NewsFeedService
    NewsFeedService.push_newsfeeds_to_cache(instance)
