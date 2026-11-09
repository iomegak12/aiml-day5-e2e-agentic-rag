"""Replayable SSE event buffer per agent run (Redis Streams, expires after EVENT_BUFFER_TTL_SECONDS).

Stream key  : agent:events:{run_id}
Entry       : {type, data(json)} - the Redis stream ID is the SSE `id`, so `Last-Event-ID` maps to XREAD.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

KEY = "agent:events:{}"


class EventRepository:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis, self._ttl = redis, ttl_seconds

    async def append(self, run_id: str, event_type: str, data: dict[str, Any]) -> str:
        key = KEY.format(run_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.xadd(key, {"type": event_type, "data": json.dumps(data, default=str, ensure_ascii=False)})
            pipe.expire(key, self._ttl)
            event_id, _ = await pipe.execute()
        return event_id.decode() if isinstance(event_id, bytes) else event_id

    async def read(self, run_id: str, after_id: str = "0-0", block_ms: int | None = None,
                   count: int = 200) -> list[tuple[str, str, dict[str, Any]]]:
        """Events after `after_id` (exclusive). With block_ms, waits up to that long for new events."""
        response = await self._redis.xread({KEY.format(run_id): after_id}, count=count, block=block_ms)
        events = []
        for _key, entries in response or []:
            for event_id, fields in entries:
                fields = {(k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                          for k, v in fields.items()}
                eid = event_id.decode() if isinstance(event_id, bytes) else event_id
                events.append((eid, fields.get("type", "message"), json.loads(fields.get("data", "{}"))))
        return events

    async def exists(self, run_id: str) -> bool:
        return bool(await self._redis.exists(KEY.format(run_id)))
