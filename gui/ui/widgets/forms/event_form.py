"""Event form."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.models.event import Event
from gui.repo import entries
from gui.repo.images import import_event_image
from gui.repo.paths import slugify
from gui.ui.widgets.image_picker import ImagePicker


class EventForm(QWidget):
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

        self._title_label = QLabel("Add Event")
        self._title_label.setObjectName("H2")
        layout.addWidget(self._title_label)

        body = QHBoxLayout()
        body.setSpacing(20)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._headline = QLineEdit()
        form.addRow("Headline *", self._headline)

        self._slug = QLineEdit()
        self._slug.setPlaceholderText(
            "Optional. Auto-generated from headline if blank."
        )
        form.addRow("Slug", self._slug)

        self._summary = QPlainTextEdit()
        self._summary.setPlaceholderText("Optional long copy below the headline.")
        self._summary.setMinimumHeight(140)
        form.addRow("Summary", self._summary)

        self._image_alt = QLineEdit()
        self._image_alt.setPlaceholderText("Defaults to the headline.")
        form.addRow("Image Alt", self._image_alt)

        body.addLayout(form, 3)

        self._image_picker = ImagePicker(
            title="Image *",
            preview_size=QSize(220, 165),
        )
        body.addWidget(self._image_picker, 2)

        layout.addLayout(body, 1)

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
        self._title_label.setText("Add Event")
        self._headline.clear()
        self._slug.clear()
        self._summary.setPlainText("")
        self._image_alt.clear()
        self._image_picker.set_existing_image_src(None)

    def open_edit(self, rel_path: str) -> None:
        event = entries.load_event(rel_path)
        self._editing_rel_path = rel_path
        self._title_label.setText("Edit Event")
        self._headline.setText(event.headline)
        self._slug.setText(event.slug or "")
        self._summary.setPlainText(event.summary or "")
        self._image_alt.setText(event.imageAlt or "")
        self._image_picker.set_existing_image_src(event.imageSrc)

    def _save(self) -> None:
        new_image: Path | None = self._image_picker.selected_path()
        existing_src = self._image_picker.existing_repo_relative()
        if not new_image and not existing_src:
            QMessageBox.warning(self, "Image required", "Please choose an event image.")
            return

        headline = self._headline.text().strip()
        slug = self._slug.text().strip() or slugify(headline)
        try:
            if new_image is not None:
                if not headline:
                    raise ValueError("Headline is required before importing an image.")
                result = import_event_image(new_image, slug=slug)
                image_src = result.repo_relative
            else:
                image_src = existing_src or ""

            event = Event(
                headline=headline,
                slug=slug or None,
                summary=self._summary.toPlainText().strip() or None,
                imageSrc=image_src,
                imageAlt=self._image_alt.text().strip() or None,
            )
        except (ValueError, ValidationError) as exc:
            QMessageBox.warning(self, "Please check the form", str(exc))
            return

        try:
            saved_rel = entries.save_event(
                event, existing_relative_path=self._editing_rel_path
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not save event", str(exc))
            return
        self.saved.emit(saved_rel)
