from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FriendshipPagination(PageNumberPagination):
    # default page size when page size is not specified in url parameters
    page_size = 20
    # default value of page_size_query_param is None
    # which means clients are not allowed to specify page sizes
    # now we are adding this configuration, so clients can designate a page size according to the scenario
    # for example, we may want different page sizes for mobile and web clients
    page_size_query_param = 'size'

    # the max size that the client can designate
    max_page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'total_results': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'has_next_page': self.page.has_next(),
            'results': data,
        })
