import os

import pytest


@pytest.fixture
def redis_url():
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
    os.environ["REDIS_URL"] = url
    yield url
