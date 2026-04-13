"""A/B tests for frontend/node_picker.py.

Only tests the Docker check stub here — the rest of node_picker
needs a running Qt event loop which is out of scope for unit tests.
"""

from frontend.node_picker import check_docker_available


class TestCheckDockerAvailable:
    def test_returns_available(self):
        expected = True
        actual = check_docker_available().available
        assert actual == expected

    def test_returns_ok_reason(self):
        expected = "ok"
        actual = check_docker_available().reason
        assert actual == expected

    def test_returns_ready_message(self):
        expected = "Docker is ready."
        actual = check_docker_available().message
        assert actual == expected
