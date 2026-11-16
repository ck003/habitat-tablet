"""Enable the custom integration in Home Assistant's test harness."""

import pytest

@pytest.fixture
def snapshot():
    return {
        "protocol": 1,
        "device_id": "ad6b2f03-05d5-46bf-8d0b-51600fa9b590",
        "name": "Living tablet",
        "model": "Lenovo TB-J606F",
        "screen_on": True,
    }
