"""A/B tests for frontend/node_picker.py.

Tests the Docker check by mocking backend.check_docker() so we
don't need a running Docker daemon or Qt event loop.
"""

from unittest.mock import patch

from store.models import DockerStatus


class TestCheckDockerAvailable:
    @patch("backend.check_docker")
    def test_returns_available_when_docker_is_up(self, mock_check):
        """When Docker is running, check_docker_available() returns OK
        without showing any dialog."""
        expected_available = True
        expected_reason = "ok"

        mock_check.return_value = DockerStatus.ok()

        from frontend.node_picker import check_docker_available

        result = check_docker_available()
        actual_available = result.available
        actual_reason = result.reason

        assert actual_available == expected_available
        assert actual_reason == expected_reason

    @patch("backend.check_docker")
    def test_passes_through_docker_status(self, mock_check):
        """When Docker is up, the returned status is exactly what
        backend.check_docker() gave us."""
        expected_message = "Docker is ready."

        mock_check.return_value = DockerStatus.ok()

        from frontend.node_picker import check_docker_available

        actual_message = check_docker_available().message
        assert actual_message == expected_message
