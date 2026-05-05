"""Job schema for ``Jobs/*.json``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Job(BaseModel):
    """A single job posting rendered on ``Jobs.html``.

    Per ``docs/DATA_MODEL.md``: ``title`` and ``summary`` are required;
    everything else is optional. ``highlights`` becomes a ``<ul>``.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=False,
    )

    # Required
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)

    # Optional
    slug: str | None = None
    unit: str | None = None
    employmentType: str | None = None
    location: str | None = None
    highlights: list[str] | None = None
    applyUrl: str | None = None
    applyLabel: str | None = None
    posted: str | None = None  # YYYY-MM-DD; sort-only, not displayed
    closingDisplay: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            k: v
            for k, v in self.model_dump(by_alias=True).items()
            if v is not None
        }
