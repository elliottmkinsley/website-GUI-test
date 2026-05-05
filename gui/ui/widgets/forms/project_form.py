"""Project form. The same model serves Featured and Page surfaces; we
show/hide the surface-specific fields based on which surface is being
edited.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import Qt, QSize, Signal
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

from gui.models.project import Project
from gui.repo import entries
from gui.repo.images import import_project_image
from gui.repo.paths import slugify
from gui.ui.widgets.image_picker import ImagePicker


class ProjectForm(QWidget):
    saved = Signal(str, str)  # rel_path, surface
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editing_rel_path: str | None = None
        self._surface: str = "featured"
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._title_label = QLabel("Add Project")
        self._title_label.setObjectName("H2")
        layout.addWidget(self._title_label)

        body = QHBoxLayout()
        body.setSpacing(20)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._title = QLineEdit()
        form.addRow("Title *", self._title)

        self._description = QPlainTextEdit()
        self._description.setMinimumHeight(120)
        form.addRow("Description *", self._description)

        self._link_url = QLineEdit()
        self._link_url.setPlaceholderText("https://...")
        form.addRow("Link URL *", self._link_url)

        self._image_alt = QLineEdit()
        self._image_alt.setPlaceholderText("Defaults to the title")
        form.addRow("Image Alt", self._image_alt)

        self._button_label = QLineEdit()
        self._button_label.setPlaceholderText("Defaults to 'Read Full Story'")
        form.addRow("Button Label", self._button_label)

        # Featured-only
        self._image_src_mobile = QLineEdit()
        self._image_src_mobile.setPlaceholderText(
            "Optional. Repo path for narrow-screen variant."
        )
        self._mobile_label = QLabel("Image (mobile)")
        form.addRow(self._mobile_label, self._image_src_mobile)

        # Page-only
        self._badge = QLineEdit()
        self._badge.setPlaceholderText("Defaults to 'Featured Story'")
        self._badge_label = QLabel("Badge")
        form.addRow(self._badge_label, self._badge)

        self._source = QLineEdit()
        self._source.setPlaceholderText("Defaults to 'Story'")
        self._source_label = QLabel("Source")
        form.addRow(self._source_label, self._source)

        self._meta = QLineEdit()
        self._meta.setPlaceholderText("Optional. e.g. 'LiDAR \u2022 Caves \u2022 Springs'")
        self._meta_label = QLabel("Meta")
        form.addRow(self._meta_label, self._meta)

        self._impact = QPlainTextEdit()
        self._impact.setPlaceholderText("Optional. Renders inside a 'Radiant impact' block.")
        self._impact.setMinimumHeight(80)
        self._impact_label = QLabel("Impact")
        form.addRow(self._impact_label, self._impact)

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

    # ------------------------------------------------------------ visibility

    def _set_surface_visibility(self) -> None:
        is_featured = self._surface == "featured"
        for label, widget in (
            (self._mobile_label, self._image_src_mobile),
        ):
            label.setVisible(is_featured)
            widget.setVisible(is_featured)
        for label, widget in (
            (self._badge_label, self._badge),
            (self._source_label, self._source),
            (self._meta_label, self._meta),
            (self._impact_label, self._impact),
        ):
            label.setVisible(not is_featured)
            widget.setVisible(not is_featured)

    # ------------------------------------------------------------------ open

    def open_create(self, surface: str) -> None:
        self._surface = surface
        self._editing_rel_path = None
        self._title_label.setText(
            f"Add Project ({'Featured slide' if surface == 'featured' else 'Projects-page card'})"
        )
        self._title.clear()
        self._description.setPlainText("")
        self._link_url.clear()
        self._image_alt.clear()
        self._button_label.clear()
        self._image_src_mobile.clear()
        self._badge.clear()
        self._source.clear()
        self._meta.clear()
        self._impact.setPlainText("")
        self._image_picker.set_existing_image_src(None)
        self._set_surface_visibility()

    def open_edit(self, rel_path: str, surface: str) -> None:
        project = entries.load_project(rel_path)
        self._surface = surface
        self._editing_rel_path = rel_path
        self._title_label.setText(
            f"Edit Project ({'Featured slide' if surface == 'featured' else 'Projects-page card'})"
        )
        self._title.setText(project.title)
        self._description.setPlainText(project.description)
        self._link_url.setText(project.linkUrl)
        self._image_alt.setText(project.imageAlt or "")
        self._button_label.setText(project.buttonLabel or "")
        self._image_src_mobile.setText(project.imageSrcMobile or "")
        self._badge.setText(project.badge or "")
        self._source.setText(project.source or "")
        self._meta.setText(project.meta or "")
        self._impact.setPlainText(project.impact or "")
        self._image_picker.set_existing_image_src(project.imageSrc)
        self._set_surface_visibility()

    # ------------------------------------------------------------------ save

    def _save(self) -> None:
        new_image: Path | None = self._image_picker.selected_path()
        existing_src = self._image_picker.existing_repo_relative()

        if not new_image and not existing_src:
            QMessageBox.warning(self, "Image required", "Please choose a project image.")
            return

        title = self._title.text().strip()
        try:
            if new_image is not None:
                if not title:
                    raise ValueError("Title is required before importing an image.")
                slug = slugify(title)
                result = import_project_image(new_image, slug=slug)
                image_src = result.repo_relative
            else:
                image_src = existing_src or ""

            kwargs = {
                "title": title,
                "description": self._description.toPlainText().strip(),
                "imageSrc": image_src,
                "linkUrl": self._link_url.text().strip(),
                "imageAlt": self._image_alt.text().strip() or None,
                "buttonLabel": self._button_label.text().strip() or None,
            }
            if self._surface == "featured":
                kwargs["imageSrcMobile"] = (
                    self._image_src_mobile.text().strip() or None
                )
            else:
                kwargs["badge"] = self._badge.text().strip() or None
                kwargs["source"] = self._source.text().strip() or None
                kwargs["meta"] = self._meta.text().strip() or None
                kwargs["impact"] = self._impact.toPlainText().strip() or None

            project = Project(**kwargs)
        except (ValueError, ValidationError) as exc:
            QMessageBox.warning(self, "Please check the form", str(exc))
            return

        try:
            saved_rel = entries.save_project(
                project,
                surface=self._surface,
                existing_relative_path=self._editing_rel_path,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not save project", str(exc))
            return

        self.saved.emit(saved_rel, self._surface)
