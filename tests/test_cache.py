import json

from app.core.cache import AgentResultCache


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttl: int | None = None

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value
        self.ttl = ttl

    def ping(self) -> bool:
        return True


def test_agent_result_cache_is_scoped_to_the_user(monkeypatch):
    monkeypatch.setenv("CACHE_TTL_SECONDS", "90")
    fake_redis = FakeRedis()
    cache = AgentResultCache(client=fake_redis)
    result = {"status": "succeeded", "run_id": "run-123"}

    cache.set(1, "Create a report", result)

    assert fake_redis.ttl == 90
    assert cache.get(1, "Create a report") == result
    assert cache.get(2, "Create a report") is None
    assert json.loads(next(iter(fake_redis.values.values()))) == result
