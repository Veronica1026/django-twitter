from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from gatekeeper.models import GateKeeper
from newsfeeds.services import NewsFeedService
from rest_framework import viewsets, status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.paginations import EndlessPagination
from ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    @method_decorator(ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request):
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        page = self.paginator.paginate_cached_list(cached_newsfeeds, request)
        # page is None means the data we get from cache is not enough to satisfy the request
        # so we instead retrieve directly from db
        if page is None:
            if GateKeeper.is_switched_on('switch_newsfeed_to_hbase'):
                page = self.paginator.paginate_hbase(HBaseNewsFeed, (request.user.id,), request)
            else:
                queryset = NewsFeed.objects.filter(user=request.user)
                page = self.paginate_queryset(queryset)

        serializer = NewsFeedSerializer(
            page,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)


