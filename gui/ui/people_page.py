"""People page: section dropdown + reorderable list + add/edit/delete.

Reorder is wired straight to ``manifest.reorder_people`` so the
manifest reflects the visible order at all times.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from gui.config import PEOPLE_GROUPS
from gui.repo import counters, entries, manifest
from gui.repo.cache_buster import bump_asset_version
from gui.repo.images import remove_headshot
from gui.ui.widgets.forms.person_form import PersonForm
from gui.ui.widgets.reorder_list import ReorderList


class PeoplePage(QWidget):
    backRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_group_key: str = PEOPLE_GROUPS[0][0]
        self._build()

    # -------------------------------------------------------- build

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 24, 36, 24)
        outer.setSpacing(16)

        # Header row
        header = QHBoxLayout()
        back = QPushButton("\u2190 Back")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        title = QLabel("People")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        helper = QLabel(
            "Choose a section, then add, edit, delete, or drag-to-reorder entries. "
            "Order changes save automatically."
        )
        helper.setObjectName("Muted")
        outer.addWidget(helper)

        self._stack = QStackedLayout()
        outer.addLayout(self._stack, 1)

        # ---- Page 0: list view ----
        self._list_view = QWidget(self)
        list_layout = QVBoxLayout(self._list_view)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(12)

        controls = QHBoxLayout()
        self._group_combo = QComboBox()
        for key, label, _folder in PEOPLE_GROUPS:
            self._group_combo.addItem(label, userData=key)
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        controls.addWidget(self._group_combo, 1)

        self._add_button = QPushButton("Add Person")
        self._add_button.setObjectName("Primary")
        self._add_button.clicked.connect(self._on_add)
        controls.addWidget(self._add_button)

        self._edit_button = QPushButton("Edit")
        self._edit_button.clicked.connect(self._on_edit)
        controls.addWidget(self._edit_button)

        self._delete_button = QPushButton("Delete")
        self._delete_button.setObjectName("Danger")
        self._delete_button.clicked.connect(self._on_delete)
        controls.addWidget(self._delete_button)
        list_layout.addLayout(controls)

        self._list = ReorderList()
        self._list.itemDoubleClicked.connect(lambda *_: self._on_edit())
        self._list.orderChanged.connect(self._on_reordered)
        list_layout.addWidget(self._list, 1)

        self._stack.addWidget(self._list_view)

        # ---- Page 1: form view ----
        self._form_view = QWidget(self)
        form_layout = QVBoxLayout(self._form_view)
        form_layout.setContentsMargins(0, 0, 0, 0)
        self._form = PersonForm()
        self._form.saved.connect(self._on_saved)
        self._form.cancelled.connect(self._show_list)
        form_layout.addWidget(self._form)
        self._stack.addWidget(self._form_view)

        self._stack.setCurrentIndex(0)

    # ----------------------------------------------------------- actions

    def refresh(self) -> None:
        self._reload_list()

    def _reload_list(self) -> None:
        rows = entries.list_people(self._current_group_key)
        self._list.set_entries(
            [(rel, p.name) for rel, p in rows]
        )

    def _on_group_changed(self, _idx: int) -> None:
        self._current_group_key = self._group_combo.currentData()
        self._reload_list()

    def _on_add(self) -> None:
        self._form.open_create(self._current_group_key)
        self._stack.setCurrentIndex(1)

    def _on_edit(self) -> None:
        rel = self._list.selected_path()
        if not rel:
            QMessageBox.information(self, "Edit Person", "Select a person first.")
            return
        try:
            self._form.open_edit(rel, self._current_group_key)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Could not open entry", str(exc))
            return
        self._stack.setCurrentIndex(1)

    def _on_delete(self) -> None:
        rel = self._list.selected_path()
        if not rel:
            QMessageBox.information(self, "Delete Person", "Select a person first.")
            return
        person = entries.load_person(rel)
        confirm = QMessageBox.question(
            self,
            "Delete Person",
            (
                f"Delete <b>{person.name}</b> from {self._group_label()}?<br><br>"
                "This removes the JSON file and the manifest entry. "
                "Image files are also removed (except blank-headshot.png)."
            ),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            entries.delete_person(
                rel, group_key=self._current_group_key, delete_file=True
            )
            if (
                person.imageSrc
                and not person.imageSrc.endswith("blank-headshot.png")
            ):
                remove_headshot(person.imageSrc)
            self._post_save_side_effects()
        except OSError as exc:
            QMessageBox.critical(self, "Could not delete person", str(exc))
            return
        self._reload_list()

    def _on_reordered(self, ordered_paths: list[str]) -> None:
        try:
            manifest.reorder_people(self._current_group_key, ordered_paths)  # type: ignore[arg-type]
            bump_asset_version()
        except OSError as exc:
            QMessageBox.critical(self, "Could not save order", str(exc))

    def _on_saved(self, rel_path: str, group_key: str) -> None:
        # If the saved person ended up in a different group, switch
        # the dropdown so the user sees them.
        if group_key != self._current_group_key:
            for i in range(self._group_combo.count()):
                if self._group_combo.itemData(i) == group_key:
                    self._group_combo.setCurrentIndex(i)
                    break
        self._post_save_side_effects()
        self._show_list()
        # Select the saved entry in the refreshed list.
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == rel_path:
                self._list.setCurrentRow(i)
                break

    def _post_save_side_effects(self) -> None:
        # Bump counter (only does work if faculty count changed) +
        # cache buster (always bumps so visitors see the change).
        try:
            counters.update_core_researchers_count()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Counter update failed", str(exc))
        try:
            bump_asset_version()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Cache-buster bump failed", str(exc))

    # ------------------------------------------------------------- helpers

    def _show_list(self) -> None:
        self._reload_list()
        self._stack.setCurrentIndex(0)

    def _group_label(self) -> str:
        for key, label, _folder in PEOPLE_GROUPS:
            if key == self._current_group_key:
                return label
        return self._current_group_key
