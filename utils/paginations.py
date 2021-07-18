from rest_framework.pagination import BasePagination
from rest_framework.response import Response


class EndlessPagination(BasePagination):
    page_size = 20

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_queryset(self, queryset, request, view=None):
        if 'created_at__gt' in request.query_params:
            # created_at__gt 用于下拉刷新时加载最新的内容进来
            # 为了简便起见，下拉刷新这里不做翻页机制，直接加载所有更新的数据
            # 实际上，如果数据很久没有更新的话，不会采用下拉更新的方式进行刷新，而是重新加载最新的数据，渲染第一页，然后用户自己翻页，查询后面的数据
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            # created_at__lt 用于向上滚屏（往下翻页）的时候加载下一页的数据
            # 寻找 created_at < created_at__lt 的objects 里按照 created_at 倒序的前 page_size + 1 个 objects
            # 多query一个object是为了判断 是否还有下一页 从而减少一次空加载

            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })