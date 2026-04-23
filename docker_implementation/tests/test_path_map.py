"""Pure unit tests for backend/ipc/path_map.py — no Docker required."""

from __future__ import annotations

import pytest
from backend.ipc.path_map import CONTAINER_ROOT, to_container_path, to_host_path


class TestToContainerPath:
    def test_posix_absolute(self):
        assert to_container_path("/home/alice/photo.jpg") == (
            "/host/home/alice/photo.jpg"
        )

    def test_posix_root(self):
        assert to_container_path("/") == CONTAINER_ROOT

    def test_posix_nested(self):
        assert to_container_path("/tmp/hello.txt") == "/host/tmp/hello.txt"

    def test_posix_collapses_double_slash(self):
        assert to_container_path("/tmp//foo") == "/host/tmp/foo"

    def test_windows_lowercase_drive(self):
        assert to_container_path(r"C:\Users\alice\photo.jpg") == (
            "/host/c/Users/alice/photo.jpg"
        )

    def test_windows_already_lowercase(self):
        assert to_container_path(r"d:\data\file.bin") == "/host/d/data/file.bin"

    def test_windows_forward_slash(self):
        assert to_container_path("C:/Users/bob/a.txt") == "/host/c/Users/bob/a.txt"

    def test_idempotent_already_container(self):
        already = "/host/home/alice/photo.jpg"
        assert to_container_path(already) == already

    def test_idempotent_container_root(self):
        assert to_container_path(CONTAINER_ROOT) == CONTAINER_ROOT

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            to_container_path("")

    def test_relative_rejected(self):
        with pytest.raises(ValueError):
            to_container_path("home/alice/photo.jpg")


class TestToHostPath:
    def test_posix_round_trip(self):
        host = "/home/alice/photo.jpg"
        assert to_host_path(to_container_path(host)) == host

    def test_posix_root_round_trip(self):
        assert to_host_path(to_container_path("/")) == "/"

    def test_windows_round_trip(self):
        host = r"C:\Users\alice\photo.jpg"
        # Windows round-trip normalises backslashes to forward slashes, so
        # compare the container->host result against the normalised input.
        assert to_host_path(to_container_path(host)) == "C:/Users/alice/photo.jpg"

    def test_windows_forward_slash_round_trip(self):
        host = "C:/Users/bob/a.txt"
        assert to_host_path(to_container_path(host)) == host

    def test_passthrough_non_container(self):
        assert to_host_path("/tmp/on_container_only") == "/tmp/on_container_only"

    def test_passthrough_leading_host_no_slash(self):
        # ``/hostfoo`` is not actually under the /host bind mount.
        assert to_host_path("/hostfoo/bar") == "/hostfoo/bar"

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            to_host_path("")


class TestIdempotence:
    def test_to_container_applied_twice_is_stable(self):
        once = to_container_path("/home/alice/photo.jpg")
        twice = to_container_path(once)
        assert once == twice

    def test_to_host_applied_twice_is_stable(self):
        once = to_host_path("/host/home/alice/photo.jpg")
        twice = to_host_path(once)
        assert once == twice
