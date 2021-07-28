from django.conf import settings
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()

        serialized_list = []
        for obj in objects:
            serialized_data = DjangoModelSerializer.serialize(obj)
            serialized_list.append(serialized_data)

        if serialized_list:
            # *serialized_list here * means pushing the elements one by one
            conn.rpush(key, *serialized_list)
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def load_objects(cls, key, queryset):
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
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # if key does not exists, we load directly from db
            # instead of pushing single object to cache
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = DjangoModelSerializer.serialize(obj)
        conn.lpush(key, serialized_data)
