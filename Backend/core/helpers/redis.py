from redis import asyncio as redis

from core.config import config

redis_url = config.REDIS_URL or f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/0"
redis_client = redis.from_url(url=redis_url, decode_responses=True)
