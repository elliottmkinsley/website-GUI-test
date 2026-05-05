"""Person schema, faithfully matching ``docs/DATA_MODEL.md``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PeopleGroupKey = Literal[
    "leadership",
    "faculty",
    "affiliation",
    "staff",
    "postdocs",
    "graduate",
]


class Person(BaseModel):
    """A single person entry under ``People/<group>/*.json``.

    Required fields (per docs): name, role, school, affiliation, focus,
    bio, imageSrc. Optional: type, homepageType, secondarySchool,
    profileUrl, imageFit, imagePosition.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=False,
    )

    # Required
    name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    school: str = Field(..., min_length=1)
    affiliation: str = Field(..., min_length=1)
    focus: str = Field(..., min_length=1)
    bio: str = Field(..., min_length=1)
    imageSrc: str = Field(..., min_length=1)

    # Optional
    type: str | None = None
    homepageType: str | None = None
    secondarySchool: str | None = None
    profileUrl: str | None = None
    imageFit: str | None = None
    imagePosition: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        """Serialize the way the website JSONs are written.

        Drops keys whose value is ``None`` so optional fields don't
        get round-tripped as ``"foo": null`` (the existing files in
        the repo simply omit absent keys).
        """
        return {
            k: v
            for k, v in self.model_dump(by_alias=True).items()
            if v is not None
        }
