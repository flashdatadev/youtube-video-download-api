import socket

import pytest


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not contact live services")

    monkeypatch.setattr(socket, "create_connection", blocked)
