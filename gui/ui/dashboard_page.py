"""Dashboard: 4 domain tiles + Publish + sign-out."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.repo import entries


class DashboardPage(QWidget):
    openPeople = Signal()
    openProjects = Signal()
    openEvents = Signal()
    openJobs = Signal()
    openPublish = Signal()
    signOutRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 36, 48, 36)
        layout.setSpacing(20)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        self._user_label = QLabel("")
        self._user_label.setObjectName("Muted")
        header.addWidget(self._user_label)
        sign_out = QPushButton("Sign Out")
        sign_out.clicked.connect(self.signOutRequested.emit)
        header.addWidget(sign_out)
        layout.addLayout(header)

        subtitle = QLabel(
            "Manage the four content domains, then publish your changes."
        )
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        # Tiles
        grid = QGridLayout()
        grid.setSpacing(16)

        self._people_tile = self._make_tile("People", "Leadership, faculty, staff, students")
        self._people_tile.clicked.connect(self.openPeople.emit)
        grid.addWidget(self._people_tile, 0, 0)

        self._projects_tile = self._make_tile(
            "Projects", "Featured slides + Projects-page cards"
        )
        self._projects_tile.clicked.connect(self.openProjects.emit)
        grid.addWidget(self._projects_tile, 0, 1)

        self._events_tile = self._make_tile("Events", "Homepage events block")
        self._events_tile.clicked.connect(self.openEvents.emit)
        grid.addWidget(self._events_tile, 1, 0)

        self._jobs_tile = self._make_tile("Jobs", "Opportunities page postings")
        self._jobs_tile.clicked.connect(self.openJobs.emit)
        grid.addWidget(self._jobs_tile, 1, 1)

        layout.addLayout(grid)

        layout.addStretch(1)

        # Publish row
        publish_row = QHBoxLayout()
        publish_row.addStretch(1)
        self._publish_button = QPushButton("Publish to website")
        self._publish_button.setObjectName("Accent")
        self._publish_button.setFixedHeight(48)
        self._publish_button.clicked.connect(self.openPublish.emit)
        publish_row.addWidget(self._publish_button)
        publish_row.addStretch(1)
        layout.addLayout(publish_row)

    def _make_tile(self, title: str, sub: str) -> QPushButton:
        btn = QPushButton(f"{title}\n0 entries\n{sub}")
        btn.setObjectName("Tile")
        btn.setMinimumHeight(140)
        btn.setSizePolicy(btn.sizePolicy().horizontalPolicy(), btn.sizePolicy().Expanding)
        return btn

    def set_user(self, username: str) -> None:
        if username:
            self._user_label.setText(f"Signed in as <b>{username}</b>")
        else:
            self._user_label.setText("")

    def refresh_summary(self) -> None:
        try:
            people = sum(
                len(entries.list_people(key))
                for key in (
                    "leadership",
                    "faculty",
                    "affiliation",
                    "staff",
                    "postdocs",
                    "graduate",
                )
            )
        except Exception:
            people = 0
        try:
            featured = len(entries.list_projects("featured"))
            page = len(entries.list_projects("page"))
        except Exception:
            featured = page = 0
        try:
            events = len(entries.list_events())
        except Exception:
            events = 0
        try:
            jobs = len(entries.list_jobs())
        except Exception:
            jobs = 0

        self._people_tile.setText(
            f"People\n{people} entries\nLeadership, faculty, staff, students"
        )
        self._projects_tile.setText(
            f"Projects\n{featured} featured | {page} on Projects page\nFeatured slides + Projects-page cards"
        )
        self._events_tile.setText(
            f"Events\n{events} entries\nHomepage events block"
        )
        self._jobs_tile.setText(
            f"Jobs\n{jobs} entries\nOpportunities page postings"
        )
