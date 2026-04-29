# runtime_logger/parser.py
import os
import re
import threading
import time

from runtime_logger.logger import get_logger

ION_LOG_PATH = "/home/ion.log"
RAW_LINE_RE = re.compile(r"\[(\d{4}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2})\]\s+\[(.)\]\s*(.*)")

# ── Pattern table ──────────────────────────────────────────────────────────
# Each entry: (compiled_regex, dedup_key, message_fn)
# dedup_key: if set, the same key won't emit again within DEDUP_WINDOW seconds
# Set to None for transfer events that should never be deduplicated.
PATTERNS = [
    (
        re.compile(r"rfxclock is running", re.IGNORECASE),
        "ion_start",
        lambda m, ctx: "ION started — node is online",
    ),
    (
        re.compile(r"tcpcli is running \[(.+?)\]", re.IGNORECASE),
        "tcpcli_start",
        lambda m, ctx: f"TCP link layer active on {m.group(1)}",
    ),
    (
        re.compile(r"Administrative endpoint terminated", re.IGNORECASE),
        "ion_stop",
        lambda m, ctx: "ION shutting down",
    ),
    (
        re.compile(
            r"This node deploys bundle protocol version (\d+)",
            re.IGNORECASE,
        ),
        "bp_version",
        lambda m, ctx: f"Bundle Protocol v{m.group(1)} active",
    ),
    (
        re.compile(r"cfdpclock is running", re.IGNORECASE),
        "cfdp_ready",
        lambda m, ctx: "CFDP engine ready",
    ),
    (
        re.compile(r"Connected to TCP socket: (.+)", re.IGNORECASE),
        "tcp_connect",
        lambda m, ctx: f"Connected to node 2 at {m.group(1)}",
    ),
    (
        re.compile(r"bputa is running", re.IGNORECASE),
        "bputa_start",
        lambda m, ctx: "CFDP bundle agent running",
    ),
    (
        re.compile(r"Can't find ION security database", re.IGNORECASE),
        "no_sec_db",
        lambda m, ctx: "⚠️  No ION security database — running without bundle security",
    ),
    (
        re.compile(r"running without bundle security", re.IGNORECASE),
        "no_sec_db",
        lambda m, ctx: None,  # suppressed — already covered by the line above
    ),
    (
        re.compile(r"Endpoint is already open", re.IGNORECASE),
        "ep_open",
        lambda m, ctx: (
            "Endpoint already open — ION may need a restart (ionstop → ionstart)"
        ),
    ),
    (
        re.compile(r"Semaphore open failed", re.IGNORECASE),
        "sem_fail",
        lambda m, ctx: "ION shared memory conflict — run ionstop and restart",
    ),
    (
        re.compile(r"CFDP can't find source file\.: (.+)", re.IGNORECASE),
        None,
        lambda m, ctx: f'File not found: "{m.group(1).strip()}" — check the file path',
    ),
    (
        re.compile(r"CFDP unable to cancel outbound FDU", re.IGNORECASE),
        None,
        lambda m, ctx: (
            f'Error sending "{ctx.get("file", "unknown")}" '
            f"to Node {ctx.get('node', '2')} — transfer cancelled"
        ),
    ),
]

DEDUP_WINDOW = 60  # seconds


class ionlog_parser:
    """
    Tails /home/ion.log in a background thread and forwards translated,
    readable messages to the spacezilla.ion logger.

    Usage:
        parser = ionlog_parser()
        parser.start()
        ...
        parser.stop()

    For CFDP transfer events (which appear in the cfdptest console, not
    ion.log), call log_transfer_event() directly from transfer_backend.py.
    Call set_current_file() before each send so the parser knows which
    file is active.
    """

    def __init__(self):
        self._log = get_logger("ion")
        self._context = {"file": None, "node": "2"}
        self._running = False
        self._thread = None
        self._last_seen = {}

    def set_current_file(self, filename: str) -> None:
        """Call from transfer_backend before each cfdp_send."""
        self._context["file"] = filename

    def log_transfer_event(
        self,
        event_type: str,
        filename: str,
        node: str,
        progress: int = None,
    ) -> None:
        messages = {
            "started": f'Sending "{filename}" to Node {node}...',
            "eof_sent": (f'All bytes sent for "{filename}" — awaiting confirmation'),
            "finished": (f'"{filename}" successfully delivered to Node {node}'),
            "error": f'Error sending "{filename}" to Node {node}',
            "cancelled": f'"{filename}" was cancelled',
        }
        msg = messages.get(event_type, f"ℹ️  [{event_type}] {filename}")
        if progress is not None:
            msg += f" ({progress} bytes)"
        self._log.info(msg)

    def start(self) -> None:
        """Start the background tailing thread."""
        self._running = True
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _should_emit(self, dedup_key: str | None) -> bool:
        if dedup_key is None:
            return True
        now = time.time()
        last = self._last_seen.get(dedup_key, 0)
        if now - last > DEDUP_WINDOW:
            self._last_seen[dedup_key] = now
            return True
        return False

    def _tail(self) -> None:
        """Wait for ion.log to exist, then tail it for new lines."""
        while not os.path.exists(ION_LOG_PATH):
            time.sleep(1)

        with open(ION_LOG_PATH, "r") as f:
            f.seek(0, 2)
            while self._running:
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue
                self._process_line(line.strip())

    def _process_line(self, line: str) -> None:
        m = RAW_LINE_RE.match(line)
        if not m:
            return

        content = m.group(3)

        for pattern, dedup_key, message_fn in PATTERNS:
            match = pattern.search(content)
            if match:
                if not self._should_emit(dedup_key):
                    return
                msg = message_fn(match, self._context)
                if msg is not None:
                    self._log.info(msg)
                return
