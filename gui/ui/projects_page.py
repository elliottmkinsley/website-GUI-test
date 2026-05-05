"""Projects page: tabs for Featured vs Page, each with reorderable list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.repo import entries, manifest
from gui.repo.cache_buster import bump_asset_version
from gui.ui.widgets.forms.project_form import ProjectForm
from gui.ui.widgets.reorder_list import ReorderList


class _ProjectsTab(QWidget):
    """One surface (Featured or Page) - list + buttons."""

    addRequested = Signal()
    editRequested = Signal()
    deleteRequested = Signal()
    orderChanged = Signal(list)

    def __init__(self, surface: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.surface = surface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        controls = QHBoxLayout()
        add = QPushButton("Add Project")
        add.setObjectName("Primary")
        add.clicked.connect(self.addRequested.emit)
        controls.addWidget(add)

        edit = QPushButton("Edit")
        edit.clicked.connect(self.editRequested.emit)
        controls.addWidget(edit)

        delete = QPushButton("Delete")
        delete.setObjectName("Danger")
        delete.clicked.connect(self.deleteRequested.emit)
        controls.addWidget(delete)

        controls.addStretch(1)
        layout.addLayout(controls)

        self.list_ = ReorderList()
        self.list_.itemDoubleClicked.connect(lambda *_: self.editRequested.emit())
        self.list_.orderChanged.connect(self.orderChanged.emit)
        layout.addWidget(self.list_, 1)

    def reload(self) -> None:
        rows = entries.list_projects(self.surface)
        self.list_.set_entries([(rel, p.title) for rel, p in rows])

    def selected_path(self) -> str | None:
        return self.list_.selected_path()


class ProjectsPage(QWidget):
    backRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 24, 36, 24)
        outer.setSpacing(16)

        # Header
        header = QHBoxLayout()
        back = QPushButton("\u2190 Back")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        title = QLabel("Projects")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        helper = QLabel(
            "Featured projects appear as homepage hero slides. "
            "Page projects appear as cards on the Projects page. "
            "An entry can live in both - they're separate JSON files."
        )
        helper.setObjectName("Muted")
        helper.setWordWrap(True)
        outer.addWidget(helper)

        # Stack: tabs view (0) and form view (1)
        self._stack = QStackedLayout()
        outer.addLayout(self._stack, 1)

        # Page 0: tabs
        tabs_view = QWidget()
        tabs_layout = QVBoxLayout(tabs_view)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()

        self._featured = _ProjectsTab("featured")
        self._featured.addRequested.connect(lambda: self._open_form_create("featured"))
        self._featured.editRequested.connect(lambda: self._open_form_edit("featured"))
        self._featured.deleteRequested.connect(lambda: self._delete("featured"))
        self._featured.orderChanged.connect(
            lambda paths: self._reordered("featured", paths)
        )
        self._tabs.addTab(self._featured, "Featured (homepage slides)")

        self._page = _ProjectsTab("page")
        self._page.addRequested.connect(lambda: self._open_form_create("page"))
        self._page.editRequested.connect(lambda: self._open_form_edit("page"))
        self._page.deleteRequested.connect(lambda: self._delete("page"))
        self._page.orderChanged.connect(lambda paths: self._reordered("page", paths))
        self._tabs.addTab(self._page, "Projects page (cards)")

        tabs_layout.addWidget(self._tabs)
        self._stack.addWidget(tabs_view)

        # Page 1: form
        form_view = QWidget()
        form_layout = QVBoxLayout(form_view)
        form_layout.setContentsMargins(0, 0, 0, 0)
        self._form = ProjectForm()
        self._form.saved.connect(self._on_saved)
        self._form.cancelled.connect(self._show_list)
        form_layout.addWidget(self._form)
        self._stack.addWidget(form_view)

        self._stack.setCurrentIndex(0)

    # --------------------------------------------------------- actions

    def refresh(self) -> None:
        self._featured.reload()
        self._page.reload()

    def _tab_for(self, surface: str) -> _ProjectsTab:
        return self._featured if surface == "featured" else self._page

    def _open_form_create(self, surface: str) -> None:
        self._form.open_create(surface)
        self._stack.setCurrentIndex(1)

    def _open_form_edit(self, surface: str) -> None:
        rel = self._tab_for(surface).selected_path()
        if not rel:
            QMessageBox.information(self, "Edit Project", "Select a project first.")
            return
        try:
            self._form.open_edit(rel, surface)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Could not open entry", str(exc))
            return
        self._stack.setCurrentIndex(1)

    def _delete(self, surface: str) -> None:
        tab = self._tab_for(surface)
        rel = tab.selected_path()
        if not rel:
            QMessageBox.information(self, "Delete Project", "Select a project first.")
            return
        project = entries.load_project(rel)
        confirm = QMessageBox.question(
            self,
            "Delete Project",
            f"Delete <b>{project.title}</b>?<br><br>"
            "Removes the JSON file and the manifest entry. "
            "The project image is left in place (it may be used elsewhere).",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            entries.delete_project(rel, surface=surface, delete_file=True)
            bump_asset_version()
        except OSError as exc:
            QMessageBox.critical(self, "Could not delete project", str(exc))
            return
        tab.reload()

    def _reordered(self, surface: str, paths: list[str]) -> None:
        try:
            manifest.reorder_projects(surface, paths)  # type: ignore[arg-type]
            bump_asset_version()
        except OSError as exc:
            QMessageBox.critical(self, "Could not save order", str(exc))

    def _on_saved(self, rel_path: str, surface: str) -> None:
        bump_asset_version()
        self._show_list()
        self._tabs.setCurrentIndex(0 if surface == "featured" else 1)
        # Highlight the saved entry
        list_ = self._tab_for(surface).list_
        for i in range(list_.count()):
            if list_.item(i).data(Qt.ItemDataRole.UserRole) == rel_path:
                list_.setCurrentRow(i)
                break

    def _show_list(self) -> None:
        self.refresh()
        self._stack.setCurrentIndex(0)
