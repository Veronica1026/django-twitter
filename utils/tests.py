from testing.testcases import TestCase
from utils.redis_client import RedisClient


class UtilsTests(TestCase):

    def setUp(self):
        RedisClient.clear()

    def test_redis_client(self):
        conn = RedisClient.get_connection()
        conn.lpush('redis_key', 1)
        conn.lpush('redis_key', 2)
        # from index 0 to the last element (-1)
        cached_list = conn.lrange('redis_key', 0, -1)
        # elements without deserialization are saved as strings so we need a prefix b (byte)
        self.assertEqual(cached_list, [b'2', b'1'])

        RedisClient.clear()
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [])