"""Pydantic v2 models for the four website data domains.

These models mirror the schemas described in ``docs/DATA_MODEL.md``.
They are the bridge between disk JSON and the form widgets.
"""

from gui.models.event import Event
from gui.models.job import Job
from gui.models.person import Person
from gui.models.project import Project

__all__ = ["Event", "Job", "Person", "Project"]
