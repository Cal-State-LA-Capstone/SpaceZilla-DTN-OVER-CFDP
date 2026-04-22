from backend.startup_checks import run_all_checks
from backend.transfer_backend import TransferBackend


class BackendFacade:
    def __init__(self):
        # transfer backend handles queueing, threading, and transfer workflow
        self.transfer_backend = TransferBackend()

    # runs backend startup checks such as pyion import and ION environment checks
    def startup_check(self) -> list[tuple[str, bool, str]]:
        return run_all_checks()

    # connects the backend to the local BP endpoint and peer CFDP entity
    def connect(
        self,
        node_number: int,
        entity_id: int,
        bp_endpoint: str,
    ) -> tuple[bool, str]:
        return self.transfer_backend.connect(
            node_number=node_number,
            entity_id=entity_id,
            bp_endpoint=bp_endpoint,
        )

    # disconnects the backend
    def disconnect(self) -> tuple[bool, str]:
        return self.transfer_backend.disconnect()

    # returns True if the transfer backend is connected
    def is_connected(self) -> bool:
        return self.transfer_backend.is_connected()

    # adds files to the queue and returns their assigned queue IDs
    def queue_files(self, file_paths: list[str]) -> list[str]:
        return self.transfer_backend.queue_files(file_paths)

    # removes a queued file before it is sent
    def remove_file(self, queue_id: str) -> bool:
        return self.transfer_backend.remove_file(queue_id)

    # clears removable files from the queue
    def clear_queue(self) -> None:
        self.transfer_backend.clear_queue()

    # returns a copy of the queue for UI display
    def get_queue(self) -> list[dict]:
        return self.transfer_backend.get_queue()

    # starts processing the queued files in a background thread
    # on_change is an optional callback that receives:
    #     on_change(queue_id, status)
    def send_files(self, on_change=None) -> tuple[bool, str]:
        return self.transfer_backend.send_files(on_change=on_change)

    def suspend(self, queue_id: str | None = None) -> tuple[bool, str]:
        return self.transfer_backend.suspend(queue_id)

    def cancel(self, queue_id: str | None = None) -> tuple[bool, str]:
        return self.transfer_backend.cancel(queue_id)

    def resume(self, queue_id: str | None = None) -> tuple[bool, str]:
        return self.transfer_backend.resume(queue_id)

    def status_indicator(self) -> str:
        return self.transfer_backend.status_indicator()

    def set_parser(self, parser) -> None:
        self.transfer_backend.set_parser(parser)
