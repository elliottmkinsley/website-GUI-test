"""Image import and WebP variant generation.

For Person entries we mirror the repo conventions documented in
``docs/guides/create-image-variants.md`` exactly:

* Base headshot lives at ``Images/People/<basename>.<ext>``.
* ``Images/People/variants/card/<basename>.webp`` at ~360x420, q80.
* ``Images/People/variants/team/<basename>.webp`` at ~600x720, q82.
* The basename matches the original *exactly*, including case.

For Projects/Events the picker drops the file into ``Images/News/`` /
``Images/Events/`` and just rewrites the JSON's ``imageSrc``. WebP
variants are not used on those surfaces.

Cropping is plain center-crop to target aspect ratio, then resized
with Lanczos. No face detection.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from gui.config import (
    WEBP_CARD_QUALITY,
    WEBP_CARD_SIZE,
    WEBP_TEAM_QUALITY,
    WEBP_TEAM_SIZE,
)
from gui.repo.paths import filesafe_basename, repo_relative
from gui.workspace import get_workspace

log = logging.getLogger(__name__)

ALLOWED_INPUT_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class HeadshotResult:
    """Filesystem outcome of importing a person's headshot."""

    base_image: Path  # Images/People/<basename>.<ext>
    card_variant: Path | None  # variants/card/<basename>.webp
    team_variant: Path | None  # variants/team/<basename>.webp

    @property
    def base_repo_relative(self) -> str:
        return repo_relative(self.base_image)


@dataclass(frozen=True)
class ImageImportResult:
    """Generic image import outcome (Project / Event)."""

    image: Path

    @property
    def repo_relative(self) -> str:
        return repo_relative(self.image)


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------


def _open_oriented(src: Path) -> Image.Image:
    """Open ``src`` and apply EXIF orientation so portraits don't end
    up sideways."""
    img = Image.open(src)
    return ImageOps.exif_transpose(img)


def _center_crop_to_aspect(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop ``img`` so it matches the aspect ratio of
    ``target_w x target_h`` exactly."""
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    if abs(src_ratio - target_ratio) < 1e-3:
        return img
    if src_ratio > target_ratio:
        # source is too wide - crop sides
        new_w = int(round(src_h * target_ratio))
        left = (src_w - new_w) // 2
        return img.crop((left, 0, left + new_w, src_h))
    # source is too tall - crop top/bottom
    new_h = int(round(src_w / target_ratio))
    top = (src_h - new_h) // 2
    return img.crop((0, top, src_w, top + new_h))


def _save_webp(
    img: Image.Image,
    target: Path,
    *,
    size: tuple[int, int],
    quality: int,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    cropped = _center_crop_to_aspect(img, *size)
    resized = cropped.resize(size, Image.Resampling.LANCZOS)
    if resized.mode in ("P", "RGBA"):
        # Convert palette/alpha to RGB to prevent WebP transparency
        # quirks on the existing site (originals are JPEGs).
        background = Image.new("RGB", resized.size, (255, 255, 255))
        if resized.mode == "RGBA":
            background.paste(resized, mask=resized.split()[3])
        else:
            background.paste(resized.convert("RGBA"))
        resized = background
    resized.save(target, format="WEBP", quality=quality, method=6)


def _unique_destination(target: Path) -> Path:
    """If a file already exists at ``target``, return a suffixed variant.

    Used for Project/Event images so we never silently overwrite an
    existing image with a different one.
    """
    if not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    n = 2
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# People (with WebP variants)
# ---------------------------------------------------------------------------


def import_headshot(
    source: Path,
    *,
    person_name: str,
    basename_override: str | None = None,
) -> HeadshotResult:
    """Copy ``source`` to ``Images/People/`` and create WebP variants.

    The destination basename matches the existing repo style:
    ``First_Last.<ext>`` (TitleCase, underscore-separated). Pass
    ``basename_override`` to use an explicit basename (must already
    be filesystem-safe).
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in ALLOWED_INPUT_EXTS:
        raise ValueError(
            f"Unsupported image format: {source.suffix}. "
            f"Allowed: {sorted(ALLOWED_INPUT_EXTS)}"
        )

    if basename_override:
        basename = filesafe_basename(basename_override)
    else:
        cleaned = filesafe_basename(person_name)
        basename = cleaned or "headshot"

    ws = get_workspace()
    images_people = ws.images_people
    images_people.mkdir(parents=True, exist_ok=True)
    dest = images_people / f"{basename}{source.suffix.lower()}"

    # If the user re-imports the same source path that is already at
    # the destination, do nothing (preserve the existing file).
    if dest.exists() and dest.resolve() == source.resolve():
        log.info("Headshot already at %s; reusing", dest)
    else:
        # Same basename + same suffix: overwrite (it's an update).
        # Same basename + different suffix: drop any siblings sharing
        # the basename so the repo doesn't end up with duplicates.
        for old in images_people.glob(f"{basename}.*"):
            if old.is_file() and old != dest:
                try:
                    old.unlink()
                except OSError as exc:
                    log.warning("Could not remove old base headshot %s: %s", old, exc)
        shutil.copy2(source, dest)

    # Generate variants from the *destination* image, not the source,
    # so the variants always match what's on disk for the website.
    card_target = ws.images_people_variants_card / f"{basename}.webp"
    team_target = ws.images_people_variants_team / f"{basename}.webp"

    card_variant: Path | None = None
    team_variant: Path | None = None
    try:
        with _open_oriented(dest) as img:
            _save_webp(
                img, card_target, size=WEBP_CARD_SIZE, quality=WEBP_CARD_QUALITY
            )
            card_variant = card_target
            _save_webp(
                img, team_target, size=WEBP_TEAM_SIZE, quality=WEBP_TEAM_QUALITY
            )
            team_variant = team_target
    except OSError as exc:
        # Variants are an optimization; the runtime falls back to the
        # base image if they're missing. Log and continue.
        log.warning("Could not generate WebP variants for %s: %s", basename, exc)

    return HeadshotResult(
        base_image=dest,
        card_variant=card_variant,
        team_variant=team_variant,
    )


def remove_headshot(image_repo_relative: str) -> None:
    """Delete a headshot and both of its WebP variants if present."""
    ws = get_workspace()
    base = ws.root / image_repo_relative
    if not base.exists():
        return
    basename = base.stem
    if base.is_file():
        try:
            base.unlink()
        except OSError as exc:
            log.warning("Could not delete base headshot %s: %s", base, exc)
    for variant in (
        ws.images_people_variants_card / f"{basename}.webp",
        ws.images_people_variants_team / f"{basename}.webp",
    ):
        if variant.exists():
            try:
                variant.unlink()
            except OSError as exc:
                log.warning("Could not delete variant %s: %s", variant, exc)


# ---------------------------------------------------------------------------
# Projects / Events (no variants)
# ---------------------------------------------------------------------------


def import_project_image(source: Path, *, slug: str) -> ImageImportResult:
    """Copy ``source`` into ``Images/News/`` named ``<slug>.<ext>``."""
    return _import_simple(source, slug=slug, dest_folder=get_workspace().images_news)


def import_event_image(source: Path, *, slug: str) -> ImageImportResult:
    """Copy ``source`` into ``Images/Events/`` named ``<slug>.<ext>``."""
    return _import_simple(source, slug=slug, dest_folder=get_workspace().images_events)


def _import_simple(
    source: Path, *, slug: str, dest_folder: Path
) -> ImageImportResult:
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in ALLOWED_INPUT_EXTS:
        raise ValueError(
            f"Unsupported image format: {source.suffix}. "
            f"Allowed: {sorted(ALLOWED_INPUT_EXTS)}"
        )
    cleaned = filesafe_basename(slug) or "image"
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest = _unique_destination(dest_folder / f"{cleaned}{source.suffix.lower()}")
    if dest.exists() and dest.resolve() == source.resolve():
        return ImageImportResult(image=dest)
    shutil.copy2(source, dest)
    return ImageImportResult(image=dest)
