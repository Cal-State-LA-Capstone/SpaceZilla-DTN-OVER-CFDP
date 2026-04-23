"""Contact list management for SpaceZilla nodes.

A contact represents a peer node that this node can communicate with.
ContactStore manages the full lifecycle: add, remove, persist, and
trigger ION contact plan updates on a live node.

Saved to: nodes/{node_id}/contacts.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from store.models import NodeConfig
from store.paths import node_dir


@dataclass
class Contact:
    contact_id: int
    name: str
    peer_entity_num: int

    # CHANGED:
    # Host-based architecture needs explicit peer addressing.
    # WHY:
    # Docker-era assumptions about internal networking are gone.
    peer_host: str
    peer_port: int = 4556

    favorite: bool = False
    last_contacted: datetime | None = None
    default_remote_dir: str | None = None
    notes: str | None = None

    def rename(self, name: str) -> None:
        self.name = name

    def set_favorite(self, favorite: bool) -> None:
        self.favorite = bool(favorite)

    def set_default_remote_dir(self, remote_dir: str) -> None:
        self.default_remote_dir = remote_dir

    def set_notes(self, notes: str) -> None:
        self.notes = notes

    def mark_contacted(self) -> None:
        self.last_contacted = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.contact_id,
            "name": self.name,
            "peer_entity_num": self.peer_entity_num,
            "peer_host": self.peer_host,
            "peer_port": self.peer_port,
            "favorite": self.favorite,
            "last_contacted": (
                self.last_contacted.isoformat() if self.last_contacted else None
            ),
            "default_remote_dir": self.default_remote_dir,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Contact":
        last_contacted = data.get("last_contacted")
        if last_contacted:
            last_contacted = datetime.fromisoformat(last_contacted)

        return cls(
            contact_id=data["id"],
            name=data["name"],
            peer_entity_num=data["peer_entity_num"],
            peer_host=data["peer_host"],
            peer_port=data.get("peer_port", 4556),
            favorite=data.get("favorite", False),
            last_contacted=last_contacted,
            default_remote_dir=data.get("default_remote_dir"),
            notes=data.get("notes"),
        )


class ContactStore:
    """Manages the contact list for a single node.

    # CHANGED:
    # This now integrates directly with the store layer layout by using node_dir().
    #
    # WHY:
    # Before, this class required an external store_root argument, which meant it
    # was not really integrated into your datastore API — it was datastore-shaped,
    # but not datastore-owned.
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id

        # CHANGED:
        # Save directly inside the same per-node datastore directory used elsewhere.
        self._path = node_dir(node_id) / "contacts.json"

        self.contacts: dict[int, Contact] = {}
        self.next_id: int = 1

    def add(
        self,
        name: str,
        peer_entity_num: int,
        peer_host: str,
        peer_port: int = 4556,
    ) -> Contact:
        contact = Contact(
            contact_id=self.next_id,
            name=name,
            peer_entity_num=peer_entity_num,
            peer_host=peer_host,
            peer_port=peer_port,
        )
        self.contacts[self.next_id] = contact
        self.next_id += 1
        self.save()
        return contact

    def get(self, contact_id: int) -> Contact:
        return self.contacts[contact_id]

    def remove(self, contact_id: int) -> Contact:
        contact = self.contacts.pop(contact_id)
        self.save()
        return contact

    def all(self) -> list[Contact]:
        return sorted(
            self.contacts.values(),
            key=lambda c: (not c.favorite, c.name),
        )

    def favorites(self) -> list[Contact]:
        return sorted(
            [c for c in self.contacts.values() if c.favorite],
            key=lambda c: c.name,
        )

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "next_id": self.next_id,
            "contacts": [c.to_dict() for c in self.contacts.values()],
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load(self) -> None:
        if not self._path.exists():
            return

        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)

        self.next_id = data.get("next_id", 1)
        self.contacts = {
            c["id"]: Contact.from_dict(c)
            for c in data.get("contacts", [])
        }

    def apply_contact(self, node_config: NodeConfig, contact: Contact) -> None:
        """Write and apply a contact plan rc for this contact to the running ION node."""
        from backend import apply_contact_plan

        apply_contact_plan(
            node_config,
            peer_host=contact.peer_host,
            peer_num=contact.peer_entity_num,
            peer_port=contact.peer_port,
        )
        contact.mark_contacted()
        self.save()

    def remove_contact(self, node_config: NodeConfig, contact: Contact) -> None:
        """Write and apply a contact removal rc to the running ION node."""
        from backend import remove_contact_plan

        remove_contact_plan(
            node_config,
            peer_host=contact.peer_host,
            peer_num=contact.peer_entity_num,
            peer_port=contact.peer_port,
        )

        # CHANGED:
        # Persist after removal workflow too, so metadata stays accurate.
        self.save()


def load_contact_store(node_id: str) -> ContactStore:
    """Convenience helper to create and load a node's contact store.

    # ADDED:
    # Small integration helper so callers can use contacts like the rest of store:
    # create/load/use, without repeating boilerplate.
    """
    store = ContactStore(node_id)
    store.load()
    return store