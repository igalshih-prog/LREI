"""Deterministic test partitions for complete slow-test CI coverage."""

import pytest


def pytest_addoption(parser):
    parser.addoption("--shard-count", type=int, default=1)
    parser.addoption("--shard-index", type=int, default=0)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    count = config.getoption("--shard-count")
    index = config.getoption("--shard-index")
    if count < 1 or not 0 <= index < count:
        raise pytest.UsageError("require shard-count >= 1 and 0 <= shard-index < shard-count")
    if count == 1:
        return
    selected, deselected = [], []
    for position, item in enumerate(sorted(items, key=lambda item: item.nodeid)):
        (selected if position % count == index else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
