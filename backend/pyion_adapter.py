class PyIonAdapter:
    def __init__(self):
        self.pyion = None

        # local connection info
        self.local_node = None
        self.local_eid = None
        self.peer_entity_nbr = None

        # BP / CFDP objects returned by pyion
        self.bp_proxy = None
        self.cfdp_proxy = None
        self.endpoint = None
        self.entity = None

    def load_pyion(self) -> tuple[bool, str]:
        """
        Import pyion lazily so the app can fail gracefully instead of crashing
        at import time.
        """
        if self.pyion is not None:
            return True, "pyion already loaded."

        try:
            import pyion

            self.pyion = pyion
            return True, "pyion loaded successfully."
        except Exception as e:
            self.pyion = None
            return False, f"Failed to import pyion: {e}"

    def connect(
        self,
        local_node: int,
        local_eid: str,
        peer_entity_nbr: int,
    ) -> tuple[bool, str]:
        """
        This sets up the connection between nodes.

        local_node:
            the local ION node number

        local_eid:
            the BP endpoint to open, such as "ipn:1.1"

        peer_entity_nbr:
            the remote / peer CFDP entity number
        """
        ok, msg = self.load_pyion()
        if not ok:
            return False, msg

        if self.entity is not None:
            return True, "Already connected."

        try:
            self.local_node = local_node
            self.local_eid = local_eid
            self.peer_entity_nbr = peer_entity_nbr

            # get proxies
            self.bp_proxy = self.pyion.get_bp_proxy(self.local_node)
            self.cfdp_proxy = self.pyion.get_cfdp_proxy(self.local_node)

            # open endpoints
            self.endpoint = self.bp_proxy.bp_open(self.local_eid)
            self.entity = self.cfdp_proxy.cfdp_open(
                self.peer_entity_nbr,
                self.endpoint,
            )

            return True, "Connected successfully."
        except Exception as e:
            self._reset_state()
            return False, f"Connection failed: {e}"

    def disconnect(self) -> tuple[bool, str]:
        """
        Reset adapter state.

        If pyion later exposes explicit close methods that you want to call,
        this is the right place to do it.
        """
        try:
            self._reset_state()
            return True, "Disconnected."
        except Exception as e:
            return False, f"Disconnect failed: {e}"

    def is_connected(self) -> bool:
        """
        Return True if a CFDP entity is currently open.
        """
        return self.entity is not None

    def register_event_handler(self, event_name: str, handler) -> tuple[bool, str]:
        """
        Register a CFDP event handler.

        transfer_backend uses this to attach a handler for queue item status
        changes while a file is being sent.
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            self.entity.register_event_handler(event_name, handler)
            return True, "Event handler registered."
        except Exception as e:
            return False, f"Registering event handler failed: {e}"

    def send_file(
        self,
        source_file: str,
        dest_file: str,
        mode: int,
    ) -> tuple[bool, str]:
        """
        Wrapper around pyion CFDP send.
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            self.entity.cfdp_send(source_file, dest_file, mode)
            return True, "File send started."
        except Exception as e:
            return False, f"Send failed: {e}"

    def request_file(
        self,
        source_name: str,
        dest_path: str,
        mode: int,
    ) -> tuple[bool, str]:
        """
        Wrapper around pyion CFDP request.
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            self.entity.cfdp_request(source_name, dest_path, mode)
            return True, "File request started."
        except Exception as e:
            return False, f"Request failed: {e}"

    def report(self) -> tuple[bool, str]:
        """
        Request a CFDP report.
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            self.entity.cfdp_report()
            return True, "Report requested."
        except Exception as e:
            return False, f"Report failed: {e}"

    def add_user_message(self, msg: str) -> tuple[bool, str]:
        """
        Add a user message to the active entity / transfer context.
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            self.entity.add_usr_message(msg)
            return True, "User message added."
        except Exception as e:
            return False, f"Adding user message failed: {e}"

    def add_filestore_request(
        self,
        action,
        file1: str,
        file2: str | None = None,
    ) -> tuple[bool, str]:
        """
        Add a filestore request to the active entity / transfer context.
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            self.entity.add_filestore_request(action, file1, file2)
            return True, "Filestore request added."
        except Exception as e:
            return False, f"Adding filestore request failed: {e}"

    def wait_for_transaction_end(
        self,
        timeout: float | None = None,
    ) -> tuple[bool, str]:
        """
        Wait for the current transaction to finish.

        Returns:
            (True, "Transaction ended.") if the transaction finished
            (False, "Transaction timed out.") if it did not
        """
        if self.entity is None:
            return False, "CFDP entity is not connected."

        try:
            finished = bool(self.entity.wait_for_transaction_end(timeout=timeout))
            if finished:
                return True, "Transaction ended."
            return False, "Transaction timed out."
        except Exception as e:
            return False, f"Wait failed: {e}"

    def _reset_state(self) -> None:
        """
        Internal helper to clear connection state.
        """
        self.bp_proxy = None
        self.cfdp_proxy = None
        self.endpoint = None
        self.entity = None

        self.local_node = None
        self.local_eid = None
        self.peer_entity_nbr = None
