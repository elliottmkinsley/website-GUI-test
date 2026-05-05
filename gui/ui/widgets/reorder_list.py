"""A drag-to-reorder ``QListWidget`` keyed by repo-relative path.

Items expose:
* a display label (typically the entry's ``name`` / ``title`` /
  ``headline``)
* a stable ``data(Qt.UserRole)`` value: the repo-relative JSON path

The widget emits ``orderChanged(list[str])`` after every successful
internal drag with the new ordered list of repo-relative paths.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem


class ReorderList(QListWidget):
    orderChanged = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAlternatingRowColors(False)
        self.setUniformItemSizes(True)

    def set_entries(self, entries: list[tuple[str, str]]) -> None:
        """Replace the list contents.

        ``entries`` is a list of ``(repo_relative_path, label)`` pairs.
        """
        self.clear()
        for rel_path, label in entries:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, rel_path)
            self.addItem(item)

    def ordered_paths(self) -> list[str]:
        return [
            self.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.count())
        ]

    def selected_path(self) -> str | None:
        item = self.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # The standard ``QListWidget`` does not expose a "drop finished"
    # signal, so we override ``dropEvent`` to emit ``orderChanged``.
    def dropEvent(self, event):  # type: ignore[override]
        super().dropEvent(event)
        self.orderChanged.emit(self.ordered_paths())
