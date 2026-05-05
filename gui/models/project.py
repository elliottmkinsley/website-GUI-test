"""Project schema (covers both Featured and Page surfaces).

The same model handles entries in ``Projects/Featured/*.json`` and
``Projects/Page/*.json``; per ``docs/DATA_MODEL.md`` the schema is
shared, only some fields are surface-specific in how they're rendered.
``imageSrcMobile`` is used only by Featured slides; ``meta``,
``impact``, ``source``, ``badge`` are used only by page cards. We
allow them on both for forward-compatibility.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectSurface = Literal["featured", "page"]


class Project(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=False,
    )

    # Required
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    imageSrc: str = Field(..., min_length=1)
    linkUrl: str = Field(..., min_length=1)

    # Optional shared
    imageAlt: str | None = None
    buttonLabel: str | None = None

    # Optional, primarily Featured
    imageSrcMobile: str | None = None

    # Optional, primarily Page
    badge: str | None = None
    source: str | None = None
    meta: str | None = None
    impact: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            k: v
            for k, v in self.model_dump(by_alias=True).items()
            if v is not None
        }
