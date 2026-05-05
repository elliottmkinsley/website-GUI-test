"""Events page: reorderable list + add/edit/delete form."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from gui.repo import entries, manifest
from gui.repo.cache_buster import bump_asset_version
from gui.ui.widgets.forms.event_form import EventForm
from gui.ui.widgets.reorder_list import ReorderList


class EventsPage(QWidget):
    backRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 24, 36, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        back = QPushButton("\u2190 Back")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        title = QLabel("Events")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        helper = QLabel(
            "These appear in the homepage Events block. The block hides "
            "itself when the list is empty, switches to a single-card "
            "layout with one entry, and to a carousel with two or more."
        )
        helper.setObjectName("Muted")
        helper.setWordWrap(True)
        outer.addWidget(helper)

        self._stack = QStackedLayout()
        outer.addLayout(self._stack, 1)

        # List view
        list_view = QWidget(self)
        list_layout = QVBoxLayout(list_view)
        list_layout.setContentsMargins(0, 0, 0, 0)

        controls = QHBoxLayout()
        add = QPushButton("Add Event")
        add.setObjectName("Primary")
        add.clicked.connect(self._on_add)
        controls.addWidget(add)
        edit = QPushButton("Edit")
        edit.clicked.connect(self._on_edit)
        controls.addWidget(edit)
        delete = QPushButton("Delete")
        delete.setObjectName("Danger")
        delete.clicked.connect(self._on_delete)
        controls.addWidget(delete)
        controls.addStretch(1)
        list_layout.addLayout(controls)

        self._list = ReorderList()
        self._list.itemDoubleClicked.connect(lambda *_: self._on_edit())
        self._list.orderChanged.connect(self._on_reordered)
        list_layout.addWidget(self._list, 1)

        self._stack.addWidget(list_view)

        # Form view
        form_view = QWidget(self)
        form_layout = QVBoxLayout(form_view)
        form_layout.setContentsMargins(0, 0, 0, 0)
        self._form = EventForm()
        self._form.saved.connect(self._on_saved)
        self._form.cancelled.connect(self._show_list)
        form_layout.addWidget(self._form)
        self._stack.addWidget(form_view)

        self._stack.setCurrentIndex(0)

    def refresh(self) -> None:
        rows = entries.list_events()
        self._list.set_entries([(rel, e.headline) for rel, e in rows])

    def _on_add(self) -> None:
        self._form.open_create()
        self._stack.setCurrentIndex(1)

    def _on_edit(self) -> None:
        rel = self._list.selected_path()
        if not rel:
            QMessageBox.information(self, "Edit Event", "Select an event first.")
            return
        try:
            self._form.open_edit(rel)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Could not open entry", str(exc))
            return
        self._stack.setCurrentIndex(1)

    def _on_delete(self) -> None:
        rel = self._list.selected_path()
        if not rel:
            QMessageBox.information(self, "Delete Event", "Select an event first.")
            return
        event = entries.load_event(rel)
        confirm = QMessageBox.question(
            self,
            "Delete Event",
            f"Delete <b>{event.headline}</b>?<br><br>"
            "Removes the JSON file and the manifest entry.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            entries.delete_event(rel, delete_file=True)
            bump_asset_version()
        except OSError as exc:
            QMessageBox.critical(self, "Could not delete event", str(exc))
            return
        self.refresh()

    def _on_reordered(self, paths: list[str]) -> None:
        try:
            manifest.reorder_events(paths)
            bump_asset_version()
        except OSError as exc:
            QMessageBox.critical(self, "Could not save order", str(exc))

    def _on_saved(self, rel_path: str) -> None:
        bump_asset_version()
        self._show_list()
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == rel_path:
                self._list.setCurrentRow(i)
                break

    def _show_list(self) -> None:
        self.refresh()
        self._stack.setCurrentIndex(0)
