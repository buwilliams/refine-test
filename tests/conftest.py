from __future__ import annotations

import pytest

from tests.support import infrastructure


@pytest.fixture(scope="session", autouse=True)
def refine_test_infrastructure(request: pytest.FixtureRequest):
    needs_refine = any(
        item.get_closest_marker("refine_cli") for item in request.session.items
    )
    if not needs_refine:
        yield
        return

    infrastructure.setup()
    try:
        yield
    finally:
        infrastructure.teardown()
