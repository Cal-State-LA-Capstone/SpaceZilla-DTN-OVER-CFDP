"""File transfer queue backed by CFDP (via pyion).

Manages a list of files waiting to be sent over a DTN link. Files go
through these statuses: Queued -> Running -> Completed/Failed/Canceled.

Previously this was all module-level globals + free functions. Now it's
wrapped in a class so you can have multiple queues (one per node) without
them stomping on each other's state.
"""

import os
import threading
import time

import pyion


class FileQueue:
    """Manages queued file transfers for a single ION node."""

    paused = False
    pause_event = threading.Event()
    pause_event.set()

    def __init__(self, node_number: int, entity_id: int, bp_endpoint: str):
        # Incrementing counter used to give each queued file a unique ID
        self.counter = 0

        # The actual queue - a list of dicts, each representing one file
        self.queue: list[dict] = []
        self.queue_lock = threading.Lock()
        self.send_thread: threading.Thread | None = None

        # CFDP handles
        self.entity = None
        self.proxy = None
        self.bp_proxy = None
        self.endpoint = None

        # Callback the UI passes in so it gets notified on status changes
        self.status_change = None

        # Tracks which file is currently mid-transfer
        self.active_id: str | None = None
        self.active_lock = threading.Lock()

        # Open the CFDP + BP connections for this node
        self.proxy = pyion.get_cfdp_proxy(node_number)
        self.bp_proxy = pyion.get_bp_proxy(node_number)
        self.endpoint = self.bp_proxy.bp_open(bp_endpoint)
        self.entity = self.proxy.cfdp_open(entity_id, self.endpoint)

    def _next_id(self):
        """Bump the counter and return the new value as a string."""
        self.counter += 1
        return str(self.counter)

    # ---- public API (called by the UI / controller) ----

    def queue_file(self, file_paths):
        """Add one or more file paths to the queue. Returns list of IDs."""
        ids = []
        with self.queue_lock:
            for path in file_paths:
                queue_id = self._next_id()
                self.queue.append(
                    {
                        "id": queue_id,
                        "path": path,
                        "fileName": os.path.basename(path),
                        "size": os.path.getsize(path) if os.path.exists(path) else 0,
                        "status": "Queued",
                    }
                )
                ids.append(queue_id)
        return ids

    def remove_file(self, queue_id):
        """Remove a file from the queue by ID. Can't remove a running transfer."""
        with self.queue_lock:
            for i, item in enumerate(self.queue):
                if item["id"] == queue_id:
                    if item["status"] == "Running":
                        return False
                    self.queue.pop(i)
                    return True
        return False

    def clear_queue(self):
        """Remove all non-active items (Queued, Failed, Canceled)."""
        with self.queue_lock:
            removable = {"Queued", "Failed", "Canceled"}
            self.queue[:] = [
                item for item in self.queue if item["status"] not in removable
            ]

    def get_queue(self):
        """Return a shallow copy of the queue (safe to read outside the lock)."""
        with self.queue_lock:
            return [item.copy() for item in self.queue]

    def status_indicator(self):
        """Return the status string of the active file, or "idle"."""
        with self.active_lock:
            if self.active_id is None:
                return "idle"
            active_id = self.active_id

        with self.queue_lock:
            item = self._get_item_by_id(active_id)
            if item:
                return item["status"]

        return "idle"

    # ---- internal helpers (not called from outside this class) ----

    def _get_item_by_id(self, queue_id):
        """Linear scan for a queue entry by its ID. Must hold queue_lock."""
        for item in self.queue:
            if item["id"] == queue_id:
                return item
        return None

    def _update_status(self, queue_id, status):
        """Set a file's status and notify the UI callback."""
        with self.queue_lock:
            item = self._get_item_by_id(queue_id)
            if item:
                item["status"] = status
        if self.status_change:
            self.status_change(queue_id, status)

    def send_files(self, on_change):
        """Kick off the background send thread. No-op if one is already running.

        on_change is a callback: on_change(queue_id, new_status) that gets
        called every time a file's status changes (so the UI can update).
        """
        if self.send_thread and self.send_thread.is_alive():
            return
        self.status_change = on_change
        self.send_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.send_thread.start()

    def _make_event(self, queue_id):
        """Build a CFDP event handler bound to a specific queue item.

        pyion fires events like FINISHED, FAULT, SUSPENDED, etc.
        We translate those into our own status strings.
        """

        # Our own implementation of suspend/cancel/resume that will
        # work on the queued files. Any file that has
        # already started sending will not be affected
        def handler(event):
            event_name = str(event)
            if "FINISHED" in event_name:
                if hasattr(event, "condition_code") and event.condition_code != 0:
                    self._update_status(queue_id, "Failed")
                else:
                    self._update_status(queue_id, "Completed")
            elif "FAULT" in event_name or "ABANDONED" in event_name:
                self._update_status(queue_id, "Failed")
            elif "SUSPENDED" in event_name:
                self._update_status(queue_id, "Queued")
            elif "RESUMED" in event_name:
                self._update_status(queue_id, "Running")

        return handler

    def suspend(self, queue_id):
        """Mark a queued file as suspended."""
        with self.queue_lock:
            item = self._get_item_by_id(queue_id)
            if item and item["status"] == "Queued":
                item["status"] = "Suspended"
        print(f"File {queue_id} suspended.")
        return 0

    def cancel(self, queue_id):
        """Mark a queued file as canceled."""
        with self.queue_lock:
            item = self._get_item_by_id(queue_id)
            if item and item["status"] == "Queued":
                item["status"] = "Canceled"
        self.pause_event.set()
        print(f"File {queue_id} cancelled.")
        return 0

    def resume(self, queue_id):
        """Move a suspended file back to queued and restart worker if needed."""
        with self.queue_lock:
            item = self._get_item_by_id(queue_id)
            if item and item["status"] == "Suspended":
                item["status"] = "Queued"

        if self.send_thread is None or not self.send_thread.is_alive():
            self.send_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
            self.send_thread.start()

        print(f"File {queue_id} resumed.")
        return 0

    def _process_queue(self):
        """Background thread loop: grab the next Queued file and send it.

        Keeps going until there are no more Queued items.
        """
        while True:
            # sleep if paused
            self.pause_event.wait()

            # Grab a snapshot of the next queued item (under lock)
            with self.queue_lock:
                next_item = next(
                    (item.copy() for item in self.queue if item["status"] == "Queued"),
                    None,
                )

            if next_item is None:
                break  # nothing left to send

            queue_id = next_item["id"]
            path = next_item["path"]
            filename = next_item["fileName"]

            with self.active_lock:
                self.active_id = queue_id

            self._update_status(queue_id, "Running")

            try:
                # Wire up event handler so we get notified of CFDP outcomes
                self.entity.register_event_handler(
                    "CFDP_ALL_EVENTS", self._make_event(queue_id)
                )
                self.entity.cfdp_send(
                    source_file=path, dest_file=f"/SZ_received_files/{filename}"
                )
                success = self.entity.wait_for_transaction_end()
                time.sleep(3)

                if not success:
                    self._update_status(queue_id, "Failed")

            except Exception as e:
                print(f"Couldn't send {filename}: {e}")
                self._update_status(queue_id, "Failed")

            with self.active_lock:
                self.active_id = None


# ============================================================================
# Legacy implementation preserved below for reference only.
# Commented out to avoid mixing the old global-function design with the new
# class-based implementation above.
# ============================================================================

"""
# This sets up the connection between nodes
def fileQueue(nodeNumber: int, entityId: int, bpEndpoint: str):
    global proxy, bpProxy, endpoint, entity
    os.makedirs("/app/SZ_received_files", exist_ok=True)
    proxy = pyion.get_cfdp_proxy(nodeNumber)
    bpProxy = pyion.get_bp_proxy(nodeNumber)
    endpoint = bpProxy.bp_open(bpEndpoint)
    entity = proxy.cfdp_open(entityId, endpoint)

# uses the queueId to remove a file from the queue before its sent
# can be tweaked so that it removes the cancelled
# file from the queue completely
# def removeFile(queueId):
#   with queueLock:
#      for i, item in enumerate(queue):
#         if item["id"] == queueId:
#            if item["status"] == "Running":
#               return False
#          queue.pop(i)
#         return True
# return False

    def get_queue(self):
        Return a shallow copy of the queue (safe to read outside the lock).
        with self.queue_lock:
            return [item.copy() for item in self.queue]

    def send_files(self, on_change):
        Kick off the background send thread. No-op if one is already running.

        on_change is a callback: on_change(queue_id, new_status) that gets
        called every time a file's status changes (so the UI can update).
        if self.send_thread and self.send_thread.is_alive():
            return
        self.status_change = on_change
        self.send_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.send_thread.start()

    def status_indicator(self):
        Return the status string of the active file, or "idle".
        with self.active_lock:
            if self.active_id is None:
                return "idle"
        with self.queue_lock:
            item = self._get_item_by_id(self.active_id)
            if item:
                return item["status"]
        return "idle"

    # ---- internal helpers (not called from outside this class) ----

    def _get_item_by_id(self, queue_id):
        Linear scan for a queue entry by its ID. Must hold queue_lock.
        for item in self.queue:
            if item["id"] == queue_id:
                return item
        return None

    def _update_status(self, queue_id, status):
        Set a file's status and notify the UI callback.
        with self.queue_lock:
            item = self._get_item_by_id(queue_id)
            if item:
                item["status"] = status
        if self.status_change:
            self.status_change(queue_id, status)

# uses background thread to send the files.
# Stores 'onChange' so we can get status updates.
# also checks for other threads.

    def sendFiles(onChange):
        global sendThread, statusChange
        print("entity in sendFiles:", entity)
        if sendThread and sendThread.is_alive():
            return
        statusChange = onChange
        sendThread = threading.Thread(target=processQueue, daemon=True)
        sendThread.start()

    def _make_event(self, queue_id):
        Build a CFDP event handler bound to a specific queue item.
        pyion fires events like FINISHED, FAULT, SUSPENDED, etc.
        We translate those into our own status strings.

# Our own implementation of suspend/cancel/resume that will
# work on the queued files. Any file that has
# already started sending will not be affected
        def handler(event):
            event_name = str(event)
            if "FINISHED" in event_name:
                if hasattr(event, "condition_code") and event.condition_code != 0:
                    self._update_status(queue_id, "Failed")
                else:
                    self._update_status(queue_id, "Completed")
            elif "FAULT" in event_name or "ABANDONED" in event_name:
                self._update_status(queue_id, "Failed")
            elif "SUSPENDED" in event_name:
                self._update_status(queue_id, "Queued")
            elif "RESUMED" in event_name:
                self._update_status(queue_id, "Running")

        return handler

    def suspend(queueId):
        with queueLock:
            item = getItemById(queueId)
            if item and item["status"] == "Queued":
                item["status"] = "Suspended"
        print(f"File {queueId} suspended.")
        return 0

    def cancel(queueId):
        with queueLock:
            for item in queue:
                if item["id"] == queueId and item["status"] == "Queued":
                    item["status"] = "Cancelled"
        pauseEvent.set()
        print(f"File {queueId} cancelled.")
        return 0

    def resume(queueId):
        global sendThread
        with queueLock:
            item = getItemById(queueId)
            if item and item["status"] == "Suspended":
                item["status"] = "Queued"
        if sendThread is None or not sendThread.is_alive():
            sendThread = threading.Thread(target=processQueue, daemon=True)
            sendThread.start()
        print(f"File {queueId} resumed.")
        return 0

    def _process_queue(self):
        Background thread loop: grab the next Queued file and send it.

        Keeps going until there are no more Queued items.
        while True:
            # Grab a snapshot of the next queued item (under lock)
            with self.queue_lock:
                next_item = next(
                    (item.copy() for item in self.queue if item["status"] == "Queued"),
                    None,
                )

            if next_item is None:
                break  # nothing left to send

            queue_id = next_item["id"]
            path = next_item["path"]
            filename = next_item["fileName"]

            with self.active_lock:
                self.active_id = queue_id
            self._update_status(queue_id, "Running")

            try:
                # Wire up event handler so we get notified of CFDP outcomes
                self.entity.register_event_handler(
                    "CFDP_ALL_EVENTS", self._make_event(queue_id)
                )
                self.entity.cfdp_send(
                    source_file=path, dest_file=f"/SZ_received_files/{filename}"
                )
                success = self.entity.wait_for_transaction_end()

                if not success:
                    self._update_status(queue_id, "Failed")

            except Exception as e:
                print(f"Couldn't send {filename}: {e}")
                self._update_status(queue_id, "Failed")

    # searches queue for a specific item in the queue by its ID.
    # If we find it it seturns the dictionary for that ID.
    # 'updateStatus' and statusIndicator' use this
    def getItemById(queueId):
        for item in queue:
            if item["id"] == queueId:
                return item
        return None

    # updates the file status in the queue and chages the 'statusChange'  variable
    def updateStatus(queueId, status):
        with queueLock:
            item = getItemById(queueId)
            if item:
                item["status"] = status
        if statusChange:
            statusChange(queueId, status)

    # cfpd event handler thasts connected to a 'queueId'
    def makeEvent(queueId):
        def handler(event):
            eventName = str(event)
            if "FINISHED" in eventName:
                if hasattr(event, "condition_code") and event.condition_code != 0:
                    updateStatus(queueId, "Failed")
                else:
                    updateStatus(queueId, "Completed")
            elif "FAULT" in eventName or "ABANDONED" in eventName:
                updateStatus(queueId, "Failed")
            elif "SUSPENDED" in eventName:
                updateStatus(queueId, "Queued")
            elif "RESUMED" in eventName:
                updateStatus(queueId, "Running")

        return handler

    # this is used for the send thread. It loops through queue looking for the next
    # file added to the queue. If it finds one it will change the status to 'Running'
    # and register the event handler and it will call 'cfdp_send'.
    # This will keep going until the queue is empty.
    def processQueue():
        global activeId
        print("Testing process queueu")
        while True:
            # sleep if paused
            pauseEvent.wait()
            with queueLock:
                nextItem = next(
                    (item.copy() for item in queue if item["status"] == "Queued"), None
                )

            print("next Item: ", nextItem)
            print("queue: ", queue)
            if nextItem is None:
                break

            queueId = nextItem["id"]
            path = nextItem["path"]
            filename = nextItem["fileName"]

            with activeLock:
                activeId = queueId
            updateStatus(queueId, "Running")

            try:
                print(f"event handler for: ,{filename}")
                entity.register_event_handler("CFDP_ALL_EVENTS", makeEvent(queueId))
                print(f"cfdp_send for {path}")
                entity.cfdp_send(
                    source_file=path, dest_file=f"/SZ_received_files/{filename}"
                )
                print("send done,waiting to end")
                success = entity.wait_for_transaction_end()
                print(f"transaction end: {success}")
                time.sleep(3)

                if success:
                    updateStatus(queueId, "Completed")
                else:
                    updateStatus(queueId, "Failed")

            except Exception as e:
                print(f"Couldn't send {filename}: {e}")
                updateStatus(queueId, "Failed")

            with activeLock:
                activeId = None
"""
