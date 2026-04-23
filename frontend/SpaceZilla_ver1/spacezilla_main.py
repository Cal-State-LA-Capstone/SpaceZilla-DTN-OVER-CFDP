from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QScrollArea, QDialogButtonBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

import os

# ADDED
from store import load_contact_store
from backend import apply_contact_plan

loader = QUiLoader()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_ui(ui_file):
    ui_path = os.path.join(BASE_DIR, ui_file)
    file = QFile(ui_path)

    if not file.exists():
        raise FileNotFoundError(f"UI file not found: {ui_path}")

    if not file.open(QFile.ReadOnly):
        raise RuntimeError(f"Could not open UI file: {ui_path}")

    window = loader.load(file)
    file.close()

    if window is None:
        raise RuntimeError(f"Failed to load UI file: {ui_path}")

    return window


class MainWindow:
    def __init__(self):
        self.window = load_ui("SpaceZilla_ver0.ui")
        self.window.setWindowTitle("SpaceZilla")

        # CHANGED: node_id will be set externally
        self.node_id = None
        self.node_config = None

        # CONTACT UI
        self.destination_filter = self.window.findChild(QLineEdit, "contact_filter")
        self.add_contact_btn = self.window.findChild(QPushButton, "add_contact_btn")
        self.contact_area = self.window.findChild(QScrollArea, "CONTACT_LIST")

        self.contact_container = QWidget()
        self.contact_layout = QVBoxLayout(self.contact_container)
        self.contact_layout.setAlignment(Qt.AlignTop)
        self.contact_container.setLayout(self.contact_layout)

        self.contact_area.setWidget(self.contact_container)
        self.contact_area.setWidgetResizable(True)

        # CHANGED: use datastore
        self.contact_store = None
        self.contacts = []

        self.add_contact_btn.clicked.connect(self.open_add_contact)

        # selected contact
        self.selected_contact = None

    def show(self):
        self.window.show()

    # ADDED: initialize contacts after node_id is set
    def init_contacts(self, node_id, node_config):
        self.node_id = node_id
        self.node_config = node_config

        self.contact_store = load_contact_store(node_id)
        self.load_contacts_from_store()

    # ADDED
    def load_contacts_from_store(self):
        self.contacts.clear()

        for i in reversed(range(self.contact_layout.count())):
            widget = self.contact_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for contact in self.contact_store.all():
            self.add_to_contact_list(contact)

    # ============================
    # ADD CONTACT
    # ============================

    def open_add_contact(self):
        self.contact_edit_window = load_ui("Contact_Info_Edit.ui")
        self.contact_edit_window.setWindowTitle("Add Contact")

        name_box = self.contact_edit_window.findChild(QLineEdit, "contact_name")
        entity_box = self.contact_edit_window.findChild(QLineEdit, "contact_entity")
        host_box = self.contact_edit_window.findChild(QLineEdit, "contact_host")
        port_box = self.contact_edit_window.findChild(QLineEdit, "contact_port")

        button_box = self.contact_edit_window.findChild(QDialogButtonBox, "buttonBox")

        button_box.accepted.connect(
            lambda: self.save_contact(name_box, entity_box, host_box, port_box)
        )
        button_box.rejected.connect(self.contact_edit_window.close)

        self.contact_edit_window.show()

    def save_contact(self, name_box, entity_box, host_box, port_box):
        name = name_box.text().strip()
        entity = entity_box.text().strip()
        host = host_box.text().strip()
        port = port_box.text().strip()

        if not name or not entity or not host:
            return

        try:
            entity = int(entity)
            port = int(port) if port else 4556
        except ValueError:
            return

        contact = self.contact_store.add(
            name=name,
            peer_entity_num=entity,
            peer_host=host,
            peer_port=port,
        )

        # ADDED: apply contact plan immediately
        try:
            apply_contact_plan(self.node_config, host, entity, port)
        except Exception as e:
            print("Failed to apply contact:", e)

        self.add_to_contact_list(contact)
        self.contact_edit_window.close()

    # ============================
    # DISPLAY CONTACT
    # ============================

    def add_to_contact_list(self, contact):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)

        name_label = QLabel(f"{contact.name} ({contact.peer_entity_num})")
        address_label = QLabel(f"{contact.peer_host}:{contact.peer_port}")

        edit_btn = QPushButton()
        delete_btn = QPushButton()

        edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        delete_btn.setIcon(QIcon.fromTheme("edit-delete"))

        edit_btn.setFixedSize(30, 26)
        delete_btn.setFixedSize(30, 26)

        edit_btn.clicked.connect(lambda: self.open_edit_contact(contact))
        delete_btn.clicked.connect(lambda: self.delete_contact(contact, row_widget))

        row_layout.addWidget(name_label)
        row_layout.addWidget(address_label)
        row_layout.addWidget(edit_btn)
        row_layout.addWidget(delete_btn)

        self.contact_layout.addWidget(row_widget)

        self.contacts.append({
            "contact": contact,
            "widget": row_widget
        })

        name_label.mousePressEvent = lambda event: self.select_contact(contact)
        address_label.mousePressEvent = lambda event: self.select_contact(contact)

    # ============================
    # DELETE
    # ============================

    def delete_contact(self, contact, row_widget):
        self.contact_store.remove(contact.contact_id)

        row_widget.setParent(None)
        self.contacts = [c for c in self.contacts if c["contact"] != contact]

    # ============================
    # SELECT
    # ============================

    def select_contact(self, contact):
        self.selected_contact = contact
        self.destination_filter.setText(
            f"{contact.name} ({contact.peer_entity_num})"
        )