"""File-pick + preview widget for selecting an image.

The widget purposely stays unopinionated about *where* the image
will eventually be copied - that's the parent form's responsibility
when it calls ``gui.repo.images.import_*``. Here we only:

1. Let the user pick a file (or drop one).
2. Show a preview at a fixed aspect.
3. Expose ``selected_path`` (an absolute path on disk) and an
   optional pre-set ``imageSrc`` string for editing existing entries.

Use ``set_existing_image_src("Images/People/Foo.jpg")`` when opening
an "Edit" form so the user sees the current image without re-picking
it.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.workspace import get_workspace


class ImagePicker(QWidget):
    """Compact image-pick + preview widget."""

    pathChosen = Signal(str)  # absolute path the user just picked
    cleared = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        preview_size: QSize | None = None,
        title: str = "Image",
    ) -> None:
        super().__init__(parent)
        self._preview_size = preview_size or QSize(180, 210)
        self._selected_path: Path | None = None
        self._existing_repo_relative: str | None = None
        self._title = title
        self._build()
        self._render()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        title_label = QLabel(self._title)
        title_label.setObjectName("Muted")
        outer.addWidget(title_label)

        body = QHBoxLayout()
        body.setSpacing(12)

        self._preview = QLabel()
        self._preview.setFrameShape(QFrame.Shape.Box)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedSize(self._preview_size)
        self._preview.setStyleSheet("background-color: #ffffff;")
        body.addWidget(self._preview)

        button_col = QVBoxLayout()
        button_col.setSpacing(6)
        button_col.addStretch(1)
        self._pick_button = QPushButton("Choose image...")
        self._pick_button.clicked.connect(self._pick)
        button_col.addWidget(self._pick_button)
        self._clear_button = QPushButton("Remove")
        self._clear_button.clicked.connect(self._clear)
        button_col.addWidget(self._clear_button)
        self._caption = QLabel("")
        self._caption.setObjectName("Muted")
        self._caption.setWordWrap(True)
        self._caption.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_col.addWidget(self._caption)
        button_col.addStretch(1)

        body.addLayout(button_col, 1)
        outer.addLayout(body)

    # ------------------------------------------------------------------ API

    def selected_path(self) -> Path | None:
        """Path of the file the user picked this session, if any."""
        return self._selected_path

    def existing_repo_relative(self) -> str | None:
        """The pre-set ``imageSrc`` from an Edit form, if any."""
        return self._existing_repo_relative

    def set_existing_image_src(self, image_src: str | None) -> None:
        """Pre-fill the preview with an image already in the repo."""
        self._existing_repo_relative = image_src
        self._selected_path = None
        self._render()

    # -------------------------------------------------------------- handlers

    def _pick(self) -> None:
        starting = str(get_workspace().root)
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Choose image",
            starting,
            "Images (*.jpg *.jpeg *.png *.webp)",
        )
        if not path_str:
            return
        self._selected_path = Path(path_str)
        self._render()
        self.pathChosen.emit(path_str)

    def _clear(self) -> None:
        self._selected_path = None
        self._existing_repo_relative = None
        self._render()
        self.cleared.emit()

    # --------------------------------------------------------------- render

    def _render(self) -> None:
        pix: QPixmap | None = None
        caption = "No image selected."
        if self._selected_path and self._selected_path.exists():
            pix = QPixmap(str(self._selected_path))
            caption = f"New: {self._selected_path.name}"
        elif self._existing_repo_relative:
            abs_path = get_workspace().root / self._existing_repo_relative
            if abs_path.exists():
                pix = QPixmap(str(abs_path))
            caption = f"Current: {self._existing_repo_relative}"
        if pix and not pix.isNull():
            self._preview.setPixmap(
                pix.scaled(
                    self._preview_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self._preview.clear()
            self._preview.setText("(no preview)")
        self._caption.setText(caption)
