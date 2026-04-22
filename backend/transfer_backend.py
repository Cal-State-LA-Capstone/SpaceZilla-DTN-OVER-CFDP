import os
import threading

from backend.pyion_adapter import PyIonAdapter
from runtime_logger import ionlog_parser


class TransferBackend:
    def __init__(self):
        self.adapter = PyIonAdapter()

        # used to keep track of files in the queue
        self.counter = 0

        # holds files
        self.queue: list[dict] = []

        # avoid threads crashing / protect queue access
        self.queue_lock = threading.Lock()

        # used so active_id doesn't crash
        self.active_lock = threading.Lock()

        # keep track of background thread
        self.send_thread = None

        # stores callback func to know when the status changes
        self.status_change_callback = None

        # Id of the file being sent
        self.active_id = None

        self.parser: ionlog_parser | None = None

    def set_parser(self, parser: ionlog_parser) -> None:
        self.parser = parser

    def connect(
        self,
        node_number: int,
        entity_id: int,
        bp_endpoint: str,
    ) -> tuple[bool, str]:
        """
        This sets up the connection between nodes.

        Delegates to pyion_adapter so all raw pyion setup stays in one place.
        """
        return self.adapter.connect(
            local_node=node_number,
            local_eid=bp_endpoint,
            peer_entity_nbr=entity_id,
        )

    def disconnect(self) -> tuple[bool, str]:
        """
        Reset transfer state and disconnect the adapter.
        """
        with self.active_lock:
            self.active_id = None

        return self.adapter.disconnect()

    def is_connected(self) -> bool:
        """
        Return True if the backend has an active CFDP connection.
        """
        return self.adapter.is_connected()

    # Increments counter by 1 for every new file added to the queue
    def next_id(self) -> str:
        self.counter += 1
        return str(self.counter)

    # takes the file path and adds it to the queue as a dictionary
    def queue_files(self, file_paths: list[str]) -> list[str]:
        ids = []

        with self.queue_lock:
            for path in file_paths:
                queue_id = self.next_id()
                self.queue.append(
                    {
                        "id": queue_id,
                        "path": path,
                        "file_name": os.path.basename(path),
                        "size": os.path.getsize(path) if os.path.exists(path) else 0,
                        "status": "Queued",
                    }
                )
                ids.append(queue_id)

        return ids

    # uses the queueId to remove a file from the queue before its sent
    def remove_file(self, queue_id: str) -> bool:
        with self.queue_lock:
            for i, item in enumerate(self.queue):
                if item["id"] == queue_id:
                    if item["status"] == "Running":
                        return False
                    self.queue.pop(i)
                    return True
        return False

    # clears the queue based on the status of each file
    def clear_queue(self) -> None:
        with self.queue_lock:
            removable = {"Queued", "Failed", "Canceled", "Completed"}
            self.queue[:] = [
                item for item in self.queue if item["status"] not in removable
            ]

    # copies the queue
    def get_queue(self) -> list[dict]:
        with self.queue_lock:
            return [item.copy() for item in self.queue]

    # uses background thread to send the files.
    # Stores 'on_change' so we can get status updates.
    # also checks for other threads.
    def send_files(self, on_change=None) -> tuple[bool, str]:
        if not self.is_connected():
            return False, "Not connected."

        if self.send_thread and self.send_thread.is_alive():
            return False, "Send thread is already running."

        self.status_change_callback = on_change
        self.send_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.send_thread.start()
        return True, "Queue processing started."

    # suspend doesnt work because the files send too fast
    def suspend(self) -> tuple[bool, str]:
        return False, "Suspend not yet implemented."

    def cancel(self) -> tuple[bool, str]:
        with self.active_lock:
            active_id = self.active_id

        if active_id is not None:
            self._update_status(active_id, "Canceled")
            return True, "Cancelled."

        return False, "No active transfer to cancel."

    # doesnt work yet
    def resume(self) -> tuple[bool, str]:
        return False, "Resume not yet implemented."

    # returns the current transfer status as a string.
    # It looks for the active file to get the file status
    def status_indicator(self) -> str:
        with self.active_lock:
            if self.active_id is None:
                return "idle"
            active_id = self.active_id

        with self.queue_lock:
            item = self._get_item_by_id(active_id)
            if item:
                return item["status"]

        return "idle"

    ##################

    # searches queue for a specific item in the queue by its ID. If we find it
    # it returns the dictionary for that ID. '_update_status' and
    # 'status_indicator' use this
    def _get_item_by_id(self, queue_id: str) -> dict | None:
        for item in self.queue:
            if item["id"] == queue_id:
                return item
        return None

    # updates the file status in the queue and changes the
    # 'status_change_callback' variable
    def _update_status(self, queue_id: str, status: str) -> None:
        with self.queue_lock:
            item = self._get_item_by_id(queue_id)
            if item:
                item["status"] = status

        if self.status_change_callback:
            self.status_change_callback(queue_id, status)

    # CFDP event handler thats connected to a 'queue_id'
    def _make_event_handler(self, queue_id: str):
        def handler(event):
            event_name = str(event)
            file_name = next((i["file_name"] for i in self.queue if i["id"] == 
                              queue_id), "unknown")

            if "FINISHED" in event_name:
                if hasattr(event, "condition_code") and event.condition_code != 0:
                    self._update_status(queue_id, "Failed")
                    if self._parser: self._parser.log_transfer_event("error",
                                                                     file_name, "2")
                else:
                    self._update_status(queue_id, "Completed")
                    if self._parser: self._parser.log_transfer_event("finished",
                                                                     file_name, "2")

            elif "FAULT" in event_name or "ABANDONED" in event_name:

                self._update_status(queue_id, "Failed")
                if self._parser: self._parser.log_transfer_event("error",
                                                                 file_name, "2")
            elif "SUSPENDED" in event_name:
                self._update_status(queue_id, "Queued")
            elif "RESUMED" in event_name:
                self._update_status(queue_id, "Running")

        return handler

    # this is used for the send thread. It loops through queue looking for the next
    # file added to the queue. If it finds one it will change the status to 'Running'
    # and register the event handler and it will call 'cfdp_send'.
    # This will keep going until the queue is empty.
    def _process_queue(self) -> None:
        while True:
            with self.queue_lock:
                next_item = next(
                    (item.copy() for item in self.queue if item["status"] == "Queued"),
                    None,
                )

            if next_item is None:
                break

            if not self.is_connected():
                self._update_status(next_item["id"], "Failed")
                break

            queue_id = next_item["id"]
            path = next_item["path"]
            file_name = next_item["file_name"]

            with self.active_lock:
                self.active_id = queue_id

            self._update_status(queue_id, "Running")
            if self._parser:
                self._parser.set_current_file(file_name)
                self._parser.log_transfer_event("started", file_name, "2")

            try:
                ok, msg = self.adapter.register_event_handler(
                    "CFDP_ALL_EVENTS",
                    self._make_event_handler(queue_id),
                )
                if not ok:
                    self._update_status(queue_id, "Failed")
                    with self.active_lock:
                        self.active_id = None
                    continue

                ok, msg = self.adapter.send_file(
                    source_file=path,
                    dest_file=f"/SZ_received_files/{file_name}",
                    mode=0,
                )

                if not ok:
                    self._update_status(queue_id, "Failed")
                else:
                    ok, msg = self.adapter.wait_for_transaction_end(timeout=10)

                    if ok:
                        self._update_status(queue_id, "Completed")
                    elif self.status_indicator() != "Canceled":
                        self._update_status(queue_id, "Failed")

            except Exception as e:
                print(f"Couldn't send {file_name}: {e}")
                self._update_status(queue_id, "Failed")

            with self.active_lock:
                self.active_id = None

        # clear thread reference when processing is done
        self.send_thread = None
