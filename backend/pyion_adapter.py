"""HTTP client that talks to ion_server.py running inside the Docker container."""

from __future__ import annotations

import httpx


class PyIonAdapter:
    def __init__(self):
        self._base_url: str | None = None

    def connect(
        self,
        local_node: int,
        local_eid: str,
        peer_entity_nbr: int,
        container_port: int | None = None,
    ) -> tuple[bool, str]:
        if container_port is not None:
            self._base_url = f"http://127.0.0.1:{container_port}"

        if self._base_url is None:
            return False, "Container port not set — cannot connect."

        try:
            resp = httpx.post(
                f"{self._base_url}/connect",
                json={
                    "local_node": local_node,
                    "local_eid": local_eid,
                    "peer_entity_nbr": peer_entity_nbr,
                },
                timeout=10.0,
            )
            data = resp.json()
            return data["ok"], data["msg"]
        except Exception as e:
            return False, f"Connection failed: {e}"

    def disconnect(self) -> tuple[bool, str]:
        if self._base_url is None:
            return True, "Not connected."
        try:
            resp = httpx.post(f"{self._base_url}/disconnect", timeout=5.0)
            data = resp.json()
            self._base_url = None
            return data["ok"], data["msg"]
        except Exception as e:
            self._base_url = None
            return False, f"Disconnect failed: {e}"

    def is_connected(self) -> bool:
        if self._base_url is None:
            return False
        try:
            resp = httpx.get(f"{self._base_url}/connected", timeout=3.0)
            return resp.json().get("connected", False)
        except Exception:
            return False

    def register_event_handler(self, event_name: str, handler) -> tuple[bool, str]:
        # ion_server handles CFDP events internally; host-side callbacks not needed
        return True, "Event handler registered."

    def send_file(
        self,
        source_file: str,
        dest_file: str,
        mode: int,
    ) -> tuple[bool, str]:
        if self._base_url is None:
            return False, "Not connected."
        try:
            resp = httpx.post(
                f"{self._base_url}/send_file",
                json={"source_file": source_file, "dest_file": dest_file, "mode": mode},
                timeout=30.0,
            )
            data = resp.json()
            return data["ok"], data["msg"]
        except Exception as e:
            return False, f"Send failed: {e}"

    def wait_for_transaction_end(
        self,
        timeout: float | None = None,
    ) -> tuple[bool, str]:
        if self._base_url is None:
            return False, "Not connected."
        t = timeout or 10.0
        try:
            resp = httpx.post(
                f"{self._base_url}/wait_for_transaction_end",
                json={"timeout": t},
                timeout=t + 5.0,
            )
            data = resp.json()
            return data["ok"], data["msg"]
        except Exception as e:
            return False, f"Wait failed: {e}"
