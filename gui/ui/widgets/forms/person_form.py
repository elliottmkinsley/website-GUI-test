"""Person form covering every field documented in DATA_MODEL.md."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from gui.config import NAU_DIRECTORY_DEFAULT_URL, PEOPLE_GROUPS
from gui.models.person import Person
from gui.repo import entries
from gui.repo.images import import_headshot, remove_headshot
from gui.ui.widgets.image_picker import ImagePicker


class PersonForm(QWidget):
    """Reusable add/edit form for a Person.

    Use ``open_create(group_key)`` for a fresh entry or
    ``open_edit(repo_relative_path, group_key)`` to pre-fill from
    disk. Emits ``saved(repo_relative_path, group_key)`` and
    ``cancelled()``.
    """

    saved = Signal(str, str)  # rel_path, group_key
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editing_rel_path: str | None = None
        self._original_group_key: str | None = None
        self._original_image_src: str | None = None
        # Image Fit / Image Position were retired from the GUI but
        # may still exist on previously-saved JSON. We preserve them
        # verbatim across edits so re-saving never silently strips
        # values an editor set outside the GUI.
        self._preserved_image_fit: str | None = None
        self._preserved_image_position: str | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._title_label = QLabel("Add Person")
        self._title_label.setObjectName("H2")
        layout.addWidget(self._title_label)

        body = QHBoxLayout()
        body.setSpacing(20)

        # Left: form fields
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._group = QComboBox()
        for key, label, _folder in PEOPLE_GROUPS:
            self._group.addItem(label, userData=key)
        form.addRow("Group *", self._group)

        self._name = QLineEdit()
        form.addRow("Name *", self._name)

        self._role = QLineEdit()
        form.addRow("Role *", self._role)

        self._type = QLineEdit()
        self._type.setPlaceholderText("Optional")
        form.addRow("Type", self._type)

        self._homepage_type = QLineEdit()
        self._homepage_type.setPlaceholderText(r"Optional. Use \n for line breaks.")
        form.addRow("Homepage Type", self._homepage_type)

        self._school = QLineEdit()
        form.addRow("School *", self._school)

        self._secondary_school = QLineEdit()
        self._secondary_school.setPlaceholderText("Optional")
        form.addRow("Secondary School", self._secondary_school)

        self._affiliation = QLineEdit()
        self._affiliation.setText("Northern Arizona University")
        form.addRow("Affiliation *", self._affiliation)

        self._focus = QLineEdit()
        self._focus.setPlaceholderText("Topic one \u2022 Topic two \u2022 Topic three")
        form.addRow("Focus *", self._focus)

        self._bio = QPlainTextEdit()
        self._bio.setPlaceholderText("Third-person bio, 3-6 sentences.")
        self._bio.setMinimumHeight(160)
        form.addRow("Bio *", self._bio)

        self._profile_url = QLineEdit()
        self._profile_url.setPlaceholderText(
            f"Leave blank to use {NAU_DIRECTORY_DEFAULT_URL}"
        )
        form.addRow("Profile URL", self._profile_url)

        body.addLayout(form, 3)

        # Right: image picker
        self._image_picker = ImagePicker(title="Headshot *")
        body.addWidget(self._image_picker, 2)

        layout.addLayout(body, 1)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.cancelled.emit)
        button_row.addWidget(cancel)
        self._save_button = QPushButton("Save")
        self._save_button.setObjectName("Primary")
        self._save_button.clicked.connect(self._save)
        button_row.addWidget(self._save_button)
        layout.addLayout(button_row)

    # ----------------------------------------------------------------- open

    def open_create(self, group_key: str) -> None:
        self._editing_rel_path = None
        self._original_group_key = None
        self._original_image_src = None
        self._preserved_image_fit = None
        self._preserved_image_position = None
        self._title_label.setText("Add Person")
        self._select_group(group_key)
        self._name.clear()
        self._role.clear()
        self._type.clear()
        self._homepage_type.clear()
        self._school.clear()
        self._secondary_school.clear()
        self._affiliation.setText("Northern Arizona University")
        self._focus.clear()
        self._bio.setPlainText("")
        self._profile_url.clear()
        self._image_picker.set_existing_image_src(None)

    def open_edit(self, rel_path: str, group_key: str) -> None:
        person = entries.load_person(rel_path)
        self._editing_rel_path = rel_path
        self._original_group_key = group_key
        self._original_image_src = person.imageSrc
        # Stash any imageFit / imagePosition that already exist on the
        # JSON. The fields no longer appear in the form (see playbook
        # gotcha #2 about silent data loss), so we just round-trip them.
        self._preserved_image_fit = person.imageFit
        self._preserved_image_position = person.imagePosition
        self._title_label.setText("Edit Person")
        self._select_group(group_key)
        self._name.setText(person.name)
        self._role.setText(person.role)
        self._type.setText(person.type or "")
        self._homepage_type.setText(person.homepageType or "")
        self._school.setText(person.school)
        self._secondary_school.setText(person.secondarySchool or "")
        self._affiliation.setText(person.affiliation)
        self._focus.setText(person.focus)
        self._bio.setPlainText(person.bio)
        self._profile_url.setText(person.profileUrl or "")
        self._image_picker.set_existing_image_src(person.imageSrc)

    def _select_group(self, group_key: str) -> None:
        for i in range(self._group.count()):
            if self._group.itemData(i) == group_key:
                self._group.setCurrentIndex(i)
                return
        self._group.setCurrentIndex(0)

    # ------------------------------------------------------------------ save

    def _save(self) -> None:
        group_key = self._group.currentData()
        name = self._name.text().strip()

        # Resolve which image to use:
        #   1. New picked file -> import + variants
        #   2. Existing imageSrc -> reuse
        #   3. Neither -> validation error
        new_image: Path | None = self._image_picker.selected_path()
        existing_src = self._image_picker.existing_repo_relative()

        if not new_image and not existing_src:
            QMessageBox.warning(
                self,
                "Headshot required",
                "Please choose a headshot image, or use the placeholder "
                "Images/People/blank-headshot.png.",
            )
            return

        try:
            if new_image is not None:
                if not name:
                    raise ValueError("Name is required before importing a headshot.")
                # Use the suggested First_Last basename for the file.
                suggested = entries.suggest_image_basename_for_person(name)
                result = import_headshot(
                    new_image, person_name=name, basename_override=suggested
                )
                image_src = result.base_repo_relative
            else:
                image_src = existing_src or ""

            # Blank Profile URL falls back to the NAU directory so
            # every person card has at least one outbound link.
            profile_url = (
                self._profile_url.text().strip() or NAU_DIRECTORY_DEFAULT_URL
            )

            person = Person(
                name=name,
                role=self._role.text().strip(),
                type=self._type.text().strip() or None,
                homepageType=self._homepage_type.text().strip() or None,
                school=self._school.text().strip(),
                secondarySchool=self._secondary_school.text().strip() or None,
                affiliation=self._affiliation.text().strip(),
                focus=self._focus.text().strip(),
                bio=self._bio.toPlainText().strip(),
                profileUrl=profile_url,
                imageSrc=image_src,
                imageFit=self._preserved_image_fit,
                imagePosition=self._preserved_image_position,
            )
        except (ValueError, ValidationError) as exc:
            QMessageBox.warning(self, "Please check the form", str(exc))
            return

        # Handle group changes for existing entries (file moves folder).
        rel_path = self._editing_rel_path
        if rel_path and self._original_group_key and group_key != self._original_group_key:
            try:
                rel_path = entries.move_person_group(
                    rel_path,
                    from_group=self._original_group_key,
                    to_group=group_key,
                )
            except (FileNotFoundError, OSError) as exc:
                QMessageBox.critical(self, "Could not move person", str(exc))
                return

        try:
            saved_rel = entries.save_person(
                person,
                group_key=group_key,
                existing_relative_path=rel_path,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not save person", str(exc))
            return

        # If the image was replaced and the old one isn't reused
        # elsewhere, clean up the previous variants. We're conservative
        # here: only remove old variants if the basename actually
        # changed (so blank-headshot.png never gets nuked).
        if (
            self._original_image_src
            and self._original_image_src != person.imageSrc
            and not self._original_image_src.endswith("blank-headshot.png")
        ):
            remove_headshot(self._original_image_src)

        self.saved.emit(saved_rel, group_key)
