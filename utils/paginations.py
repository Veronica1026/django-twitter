from dateutil import parser
from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from django.conf import settings
from utils.time_constants import MAX_TIMESTAMP


class EndlessPagination(BasePagination):
    page_size = 20

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_ordered_list(self, reverse_ordered_list, request):
        if 'created_at__gt' in request.query_params:
            # 兼容 iso 格式和 int 格式的时间戳
            try:
                created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
            except ValueError:
                created_at__gt = int(request.query_params['created_at__gt'])

            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            # 兼容 iso 格式和 int 格式的时间戳
            try:
                created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            except ValueError:
                created_at__lt = int(request.query_params['created_at__lt'])

            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                # didn't find any satisfying objects, return empty array
                # this else is corresponding with for, refer to the python grammar "for-else"
                reverse_ordered_list = []
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index: index + self.page_size]

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

    def paginate_hbase(self, hb_model, row_key_prefix, request):
        if 'created_at__gt' in request.query_params:
            # created_at__gt is used to load the latest content when scrolling down
            # to simplify it, we don't do pagination. rather, we load all the latest content
            # because if the data has not been updated for a while
            # we won't do scroll down. We will just load all the new data all over again
            created_at__gt = request.query_params['created_at__gt']
            start = (*row_key_prefix, created_at__gt)
            stop = (*row_key_prefix, MAX_TIMESTAMP)
            objects = hb_model.filter(start=start, stop=stop)
            if len(objects) and objects[0].created_at == int(created_at__gt):
                objects = objects[:0:-1]
            else:
                objecs = objects[::-1]
            self.has_next_page = False
            return objects

        if 'created_at__lt' in request.query_params:
            # created_at__lt 用于向上滚屏（往下翻页）的时候加载下一页的数据
            # 寻找 timestamp < created_at__lt 的 objects 里按照 timestamp 倒序的前 page_size + 1 个 objects
            # 比如目前的 timestamp 列表是 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] 如果 created_at__lt=5, page_size = 2
            # 则应该返回 [4, 3, 2]，多返回一个 object 的原因是为了判断是否还有下一页从而减少一次空加载。
            # 由于 hbase 只支持 <= 的查询而不支持 <, 因此我们还需要再多取一个 item 保证 < 的 item 有 page_size + 1 个
            created_at__lt = request.query_params['created_at__lt']
            start = (*row_key_prefix, created_at__lt)
            stop = (*row_key_prefix, None)
            objects = hb_model.filter(start=start, stop=stop, limit=self.page_size + 2, reverse=True)
            if len(objects) and objects[0].created_at == int(created_at__lt):
                objects = objects[1:]
            if len(objects) > self.page_size:
                self.has_next_page = True
                objects = objects[:-1]
            else:
                self.has_next_page = False
            return objects

        # no any other params, load the latest page by default
        prefix = (*row_key_prefix, None)
        objects = hb_model.filter(prefix=prefix, limit=self.page_size + 1, reverse=True)
        if len(objects) > self.page_size:
            self.has_next_page = True
            objects = objects[:-1]
        else:
            self.has_next_page = False
        return objects

    def paginate_cached_list(self, cached_list, request):
        paginated_list = self.paginate_ordered_list(cached_list, request)
        # if scroll down, paginate_list contains all the latest data, we do nothing and return it directly
        if 'created_at__gt' in request.query_params:
            return paginated_list
        # if we have next page, it means we have more data inside cached_list, also return them
        if self.has_next_page:
            return paginated_list
        # if cached_list is not long enough to hit the length limit, it means all the data is cached
        if (len(cached_list) < settings.REDIS_LIST_LENGTH_LIMIT):
            return paginated_list
        # if we enter here, it means, there might be data that is inside db, but not inside cache.
        # we need to query them in db
        return None

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })