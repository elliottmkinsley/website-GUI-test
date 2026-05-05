"""Job form. Highlights are an editable string list rendered via a
small inline list widget so each bullet stays a single string in the
JSON output."""

from __future__ import annotations

from datetime import date

from pydantic import ValidationError
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from gui.models.job import Job
from gui.repo import entries


class _HighlightsEditor(QWidget):
    """Small inline editor for the ``highlights`` string list."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setMinimumHeight(120)
        layout.addWidget(self._list)

        row = QHBoxLayout()
        add = QPushButton("Add")
        add.clicked.connect(self._add)
        row.addWidget(add)
        edit = QPushButton("Edit")
        edit.clicked.connect(self._edit)
        row.addWidget(edit)
        delete = QPushButton("Remove")
        delete.clicked.connect(self._remove)
        row.addWidget(delete)
        row.addStretch(1)
        layout.addLayout(row)

    def _add(self) -> None:
        text, ok = QInputDialog.getMultiLineText(
            self, "Add highlight", "Highlight bullet:"
        )
        if ok and text.strip():
            item = QListWidgetItem(text.strip())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(item)

    def _edit(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Edit highlight", "Highlight bullet:", item.text()
        )
        if ok and text.strip():
            item.setText(text.strip())

    def _remove(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        self._list.takeItem(row)

    def values(self) -> list[str]:
        return [
            self._list.item(i).text().strip()
            for i in range(self._list.count())
            if self._list.item(i).text().strip()
        ]

    def set_values(self, values: list[str] | None) -> None:
        self._list.clear()
        for value in values or []:
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(item)


class JobForm(QWidget):
    saved = Signal(str)
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editing_rel_path: str | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._title_label = QLabel("Add Job")
        self._title_label.setObjectName("H2")
        layout.addWidget(self._title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._title = QLineEdit()
        form.addRow("Title *", self._title)

        self._slug = QLineEdit()
        self._slug.setPlaceholderText("Optional. Auto-generated from title if blank.")
        form.addRow("Slug", self._slug)

        self._unit = QLineEdit()
        self._unit.setPlaceholderText("Optional. Org/department line.")
        form.addRow("Unit", self._unit)

        self._employment = QLineEdit()
        self._employment.setPlaceholderText("Optional. e.g. 'Summer 2026'.")
        form.addRow("Employment Type", self._employment)

        self._location = QLineEdit()
        self._location.setPlaceholderText("Optional.")
        form.addRow("Location", self._location)

        self._summary = QPlainTextEdit()
        self._summary.setMinimumHeight(140)
        form.addRow("Summary *", self._summary)

        self._highlights = _HighlightsEditor()
        form.addRow("Highlights", self._highlights)

        self._apply_url = QLineEdit()
        self._apply_url.setPlaceholderText(
            "Optional. e.g. mailto:radiant@nau.edu?subject=Application"
        )
        form.addRow("Apply URL", self._apply_url)

        self._apply_label = QLineEdit()
        self._apply_label.setPlaceholderText("Defaults to 'Apply'.")
        form.addRow("Apply Label", self._apply_label)

        self._posted = QDateEdit()
        self._posted.setCalendarPopup(True)
        self._posted.setDisplayFormat("yyyy-MM-dd")
        self._posted.setDate(QDate.currentDate())
        form.addRow("Posted", self._posted)

        self._closing = QLineEdit()
        self._closing.setPlaceholderText("Optional. e.g. 'Closing April 30, 2026'.")
        form.addRow("Closing Display", self._closing)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.cancelled.emit)
        button_row.addWidget(cancel)
        save = QPushButton("Save")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        button_row.addWidget(save)
        layout.addLayout(button_row)

    def open_create(self) -> None:
        self._editing_rel_path = None
        self._title_label.setText("Add Job")
        self._title.clear()
        self._slug.clear()
        self._unit.clear()
        self._employment.clear()
        self._location.clear()
        self._summary.setPlainText("")
        self._highlights.set_values([])
        self._apply_url.clear()
        self._apply_label.clear()
        self._posted.setDate(QDate.currentDate())
        self._closing.clear()

    def open_edit(self, rel_path: str) -> None:
        job = entries.load_job(rel_path)
        self._editing_rel_path = rel_path
        self._title_label.setText("Edit Job")
        self._title.setText(job.title)
        self._slug.setText(job.slug or "")
        self._unit.setText(job.unit or "")
        self._employment.setText(job.employmentType or "")
        self._location.setText(job.location or "")
        self._summary.setPlainText(job.summary)
        self._highlights.set_values(job.highlights or [])
        self._apply_url.setText(job.applyUrl or "")
        self._apply_label.setText(job.applyLabel or "")
        if job.posted:
            qd = QDate.fromString(job.posted, "yyyy-MM-dd")
            if qd.isValid():
                self._posted.setDate(qd)
        else:
            self._posted.setDate(QDate.currentDate())
        self._closing.setText(job.closingDisplay or "")

    def _save(self) -> None:
        try:
            highlights = self._highlights.values()
            job = Job(
                title=self._title.text().strip(),
                slug=self._slug.text().strip() or None,
                unit=self._unit.text().strip() or None,
                employmentType=self._employment.text().strip() or None,
                location=self._location.text().strip() or None,
                summary=self._summary.toPlainText().strip(),
                highlights=highlights or None,
                applyUrl=self._apply_url.text().strip() or None,
                applyLabel=self._apply_label.text().strip() or None,
                posted=self._posted.date().toString("yyyy-MM-dd"),
                closingDisplay=self._closing.text().strip() or None,
            )
        except (ValueError, ValidationError) as exc:
            QMessageBox.warning(self, "Please check the form", str(exc))
            return
        try:
            saved_rel = entries.save_job(
                job, existing_relative_path=self._editing_rel_path
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not save job", str(exc))
            return
        self.saved.emit(saved_rel)
