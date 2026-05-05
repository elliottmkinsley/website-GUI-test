"""Event schema for ``Events/*.json``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    """A single event entry rendered on the homepage Events block.

    Per ``docs/DATA_MODEL.md``: ``headline`` is required (or ``title``
    as a documented fallback) and ``imageSrc`` is required; everything
    else is optional. We standardize on ``headline`` here - a JSON
    file using only ``title`` is migrated by the loader.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=False,
    )

    # Required
    headline: str = Field(..., min_length=1)
    imageSrc: str = Field(..., min_length=1)

    # Optional
    slug: str | None = None
    summary: str | None = None
    imageAlt: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            k: v
            for k, v in self.model_dump(by_alias=True).items()
            if v is not None
        }
