from rest_framework import viewsets, status
from rest_framework.decorators import permission_classes
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.paginations import EndlessPagination

class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        # user-defined queryset, since newsfeed check is accessibility limited
        # we can only check newsfeeds of user=currently-logged-in-user
        # can also be self.request.user.newsfeed_set.all()
        # but NewsFeed.objects.filter() is easier to understand
        return NewsFeed.objects.filter(user=self.request.user)

    def list(self, request):
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = NewsFeedSerializer(
            queryset,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)


