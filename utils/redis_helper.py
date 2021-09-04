from django.conf import settings
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()

        serialized_list = []
        # we cache at most REDIS_LIST_LENGTH_LIMIT objects
        # if we need more, we read from db
        # REDIS_LIST_LENGTH_LIMIT is usually a big enough number(like 1000) to satisfy normal needs
        # only a small number of users will check more than 1000 data, so it's not a huge problem to read those from db
        for obj in objects:
            serialized_data = DjangoModelSerializer.serialize(obj)
            serialized_list.append(serialized_data)

        if serialized_list:
            # *serialized_list here * means pushing the elements one by one
            conn.rpush(key, *serialized_list)
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def load_objects(cls, key, queryset):
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()

        # if exists in cache, we retrieve it and return
        if conn.exists(key):
            serialized_list = conn.lrange(key, 0, -1)
            objects = []
            for serialized_data in serialized_list:
                deserialized_obj = DjangoModelSerializer.deserialize(serialized_data)
                objects.append(deserialized_obj)
            return objects

        cls._load_objects_to_cache(key, queryset)

        # convert to list, in order to keep the return type consistent, because the data inside redis is list
        return list(queryset)

    @classmethod
    def push_objects(cls, key, obj, queryset):
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # if key does not exists, we load directly from db
            # instead of pushing single object to cache
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = DjangoModelSerializer.serialize(obj)
        conn.lpush(key, serialized_data)
        conn.ltrim(key, 0, settings.REDIS_LIST_LENGTH_LIMIT - 1)

    @classmethod
    def get_count_key(cls, obj, attr):
        return '{}.{}:{}'.format(obj.__class__.__name__, attr, obj.id)

    @classmethod
    def incr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        if not conn.exists(key):
            # back fill from db to cache
            # we don't do +1 operation here, we need to ensure that before we call decr_count
            # obj.attr is already updated in db
            obj.refresh_from_db()
            conn.set(key, getattr(obj, attr))
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
            return getattr(obj, attr)
        return conn.incr(key)

    @classmethod
    def decr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        if not conn.exists(key):
            obj.refresh_from_db()
            # back fill from db to cache
            # we don't do +1 operation here, we need to ensure that before we call decr_count
            # obj.attr is already updated in db
            conn.set(key, getattr(obj, attr))
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
            return getattr(obj, attr)
        return conn.decr(key)

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        count = conn.get(key)
        if count is not None:
            return int(count)

        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(key, count)
        return count


