import os 
import sys 
sys.path.append(os.path.basename(''))

from redis import Redis
from redis.exceptions import RedisError
from utils.logger import get_logger
import json

### REDIS Connection params for caching
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_USERNAME = os.environ.get("REDIS_USERNAME", None)
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

REDIS_HOST = "redis-12798.c9.us-east-1-2.ec2.redns.redis-cloud.com"
REDIS_PORT = 12798
REDIS_DB = 0
REDIS_USERNAME = "default"
REDIS_PASSWORD = "s8p9cAr0THaMNbDla7OPbXdIzVHGIbqP"



class RedisHelper:
    def __init__(self):
        try:
            self.logger = get_logger("REDISHELPER")
            self.redis = Redis(
                host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD
            )
            self.logger.debug(f"Successfully initialized redis helper...")
        except Exception as e:
            self.logger.exception(e)
            raise e

    def fetch_key(self, key: str, data_type: str):
        """
        Fetches a value from Redis based on its type.

        Args:
            key (str): The Redis key to fetch.
            data_type (str): The type of the data. Can be 'json', 'list', or 'hash'.

        Returns:
            The value stored in Redis for the given key, or None if the key doesn't exist.

        Raises:
            ValueError: If an unsupported data_type is provided.
            RedisError: If there is an issue communicating with Redis.
        """
        try:
            if data_type == "json":
                value = self.redis.get(key)
                if value is not None:
                    return json.loads(
                        value
                    )  # Parse the JSON string into a Python object
                return None

            elif data_type == "list":
                byte_list = self.redis.lrange(key, 0, -1)  # Fetch the entire list
                return [item.decode("utf-8") for item in byte_list]

            elif data_type == "hash":
                byte_hash = self.redis.hgetall(key)
                return {
                    k.decode("utf-8"): v.decode("utf-8") for k, v in byte_hash.items()
                }
            else:
                raise ValueError(f"Unsupported data type: {data_type}")

        except RedisError as e:
            self.logger.exception(
                f"Error fetching key '{key}' of type '{data_type}' from Redis."
            )
            raise e
        
    def _get_random_value(self, key: str):
        """
        Retrieves a random value from a Redis list.

        Args:
            key (str): The Redis key of the list.

        Returns:
            str: A random value from the list.

        Raises:
            RedisError: If there is an issue communicating with Redis.
        """
        try:
            value = self.redis.srandmember(key)
            return value.decode("utf-8") if value else None
        except RedisError as e:
            self.logger.exception(
                f"Error retrieving random value from Redis list '{key}'."
            )
            raise e

