"""
ion_server.py — runs inside the Docker container alongside ION.

Wraps pyion operations as HTTP endpoints so the host PyIonAdapter
can drive CFDP transfers without importing pyion on the host.
"""

import re
import subprocess
import threading

import uvicorn
from fastapi import FastAPI

app = FastAPI()


class IonState:
    def __init__(self):
        self.bp_proxy = None
        self.cfdp_proxy = None
        self.endpoint = None
        self.entity = None
        self.transfer_status = "idle"  # idle | running | completed | failed | canceled
        self.lock = threading.Lock()


state = IonState()


@app.post("/connect")
async def connect(body: dict):
    try:
        import pyion

        local_node = body["local_node"]
        local_eid = body["local_eid"]
        peer_entity_nbr = body["peer_entity_nbr"]

        state.bp_proxy = pyion.get_bp_proxy(local_node)
        state.cfdp_proxy = pyion.get_cfdp_proxy(local_node)
        state.endpoint = state.bp_proxy.bp_open(local_eid)
        state.entity = state.cfdp_proxy.cfdp_open(peer_entity_nbr, state.endpoint)

        return {"ok": True, "msg": "Connected successfully."}
    except Exception as e:
        return {"ok": False, "msg": f"Connection failed: {e}"}


@app.get("/connected")
async def connected():
    return {"connected": state.entity is not None}


@app.post("/disconnect")
async def disconnect():
    try:
        state.entity = None
        state.endpoint = None
        state.cfdp_proxy = None
        state.bp_proxy = None
        return {"ok": True, "msg": "Disconnected."}
    except Exception as e:
        return {"ok": False, "msg": f"Disconnect failed: {e}"}


@app.post("/send_file")
async def send_file(body: dict):
    if state.entity is None:
        return {"ok": False, "msg": "Not connected."}

    source_file = body["source_file"]
    dest_file = body["dest_file"]
    mode = body.get("mode", 0)

    def event_handler(event):
        event_name = str(event)
        if "FINISHED" in event_name:
            if hasattr(event, "condition_code") and event.condition_code != 0:
                state.transfer_status = "failed"
            else:
                state.transfer_status = "completed"
        elif "FAULT" in event_name or "ABANDONED" in event_name:
            state.transfer_status = "failed"
        elif "SUSPENDED" in event_name:
            state.transfer_status = "suspended"
        elif "RESUMED" in event_name:
            state.transfer_status = "running"

    try:
        state.entity.register_event_handler("CFDP_ALL_EVENTS", event_handler)
        state.transfer_status = "running"
        state.entity.cfdp_send(source_file, dest_file, mode)
        return {"ok": True, "msg": "File send started."}
    except Exception as e:
        state.transfer_status = "failed"
        return {"ok": False, "msg": f"Send failed: {e}"}


@app.post("/wait_for_transaction_end")
async def wait_for_transaction_end(body: dict):
    if state.entity is None:
        return {"ok": False, "msg": "Not connected."}

    timeout = body.get("timeout", 10)

    try:
        finished = bool(state.entity.wait_for_transaction_end(timeout=timeout))
        if finished:
            return {"ok": True, "msg": "Transaction ended."}
        return {"ok": False, "msg": "Transaction timed out."}
    except Exception as e:
        return {"ok": False, "msg": f"Wait failed: {e}"}


@app.get("/transfer_status")
async def transfer_status():
    return {"status": state.transfer_status}


@app.post("/cancel")
async def cancel():
    state.transfer_status = "canceled"
    return {"ok": True, "msg": "Cancelled."}


@app.post("/suspend")
async def suspend():
    return {"ok": False, "msg": "Suspend not yet implemented."}


@app.post("/resume")
async def resume():
    return {"ok": False, "msg": "Resume not yet implemented."}


def _parse_rc_sections(rc_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in rc_text.splitlines():
        m = re.match(r"^##\s+begin\s+(\w+)", line)
        if m:
            current = m.group(1)
            buf = []
        elif re.match(r"^##\s+end\s+", line):
            if current:
                sections[current] = "\n".join(buf).strip()
            current = None
            buf = []
        elif current is not None:
            buf.append(line)
    return sections


@app.post("/apply_contact_plan")
async def apply_contact_plan(body: dict):
    rc_text = body.get("rc_text", "")
    sections = _parse_rc_sections(rc_text)
    for admin_cmd in ("ionadmin", "ltpadmin", "bpadmin", "ipnadmin", "cfdpadmin"):
        content = sections.get(admin_cmd, "").strip()
        if not content:
            continue
        try:
            result = subprocess.run(
                [admin_cmd],
                input=content + "\n",
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode != 0:
                return {"ok": False, "msg": f"{admin_cmd} failed: {result.stderr.strip()}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "msg": f"{admin_cmd} timed out after 20s"}
        except Exception as e:
            return {"ok": False, "msg": f"{admin_cmd} error: {e}"}
    return {"ok": True, "msg": "Contact plan applied."}


@app.post("/connect_cfdp")
async def connect_cfdp(body: dict):
    if state.cfdp_proxy is None or state.endpoint is None:
        return {"ok": False, "msg": "Not connected to ION."}
    try:
        peer_entity_nbr = body["peer_entity_nbr"]
        state.entity = state.cfdp_proxy.cfdp_open(peer_entity_nbr, state.endpoint)
        return {"ok": True, "msg": f"CFDP opened to entity {peer_entity_nbr}."}
    except Exception as e:
        return {"ok": False, "msg": f"CFDP connect failed: {e}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
