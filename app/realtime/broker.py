import asyncio
import json

import redis.asyncio as redis

from app.core.config import settings
from app.realtime.manager import manager


class NotificationBroker:
    def __init__(self) -> None:
        self.redis: redis.Redis | None = None
        self.listener_task: asyncio.Task | None = None

    async def start(self) -> None:
        if not settings.redis_enabled:
            return
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        await self.redis.ping()
        self.listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        if self.redis:
            await self.redis.aclose()

    async def publish(self, user_id: int, payload: dict) -> None:
        envelope = {"user_id": user_id, "payload": payload}
        if self.redis:
            await self.redis.publish(settings.redis_channel, json.dumps(envelope))
        else:
            await manager.send_to_user(user_id, payload)

    async def _listen(self) -> None:
        if self.redis is None:
            return
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(settings.redis_channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                envelope = json.loads(message["data"])
                await manager.send_to_user(envelope["user_id"], envelope["payload"])
        finally:
            await pubsub.unsubscribe(settings.redis_channel)
            await pubsub.aclose()


broker = NotificationBroker()
