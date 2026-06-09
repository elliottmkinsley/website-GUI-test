"""Insert a "macOS SHA-256" line into a GitHub Release body.

Used by the macOS build job in ``.github/workflows/release.yml``
right after the DMG is uploaded. The Windows job creates the
release with a body that includes a ``**Windows SHA-256:**`` line;
this script reads the current body via stdin (passed by ``gh
release view``), splices an analogous ``**macOS SHA-256:**`` line
in immediately after it, and writes the new body to stdout for
``gh release edit --notes-file`` to consume.

Why a dedicated script and not an inline heredoc in the workflow?
YAML's ``run: |`` block preserves the YAML's indentation, which
would prefix every heredoc line with spaces and break Python's
indentation rules. Extracting to a script also makes the splice
logic testable and lets a maintainer dry-run it locally.

Usage:

    cat current_body.md | python scripts/insert_dmg_hash_in_body.py \\
        --sha256 d41d8cd98f00b204e9800998ecf8427e \\
        --dmg-name RadiantContentGUI-0.3.0.dmg \\
        > new_body.md
"""

from __future__ import annotations

import argparse
import sys

WINDOWS_MARKER = "**Windows SHA-256:**"


def splice(body: str, *, sha256: str, dmg_name: str) -> str:
    """Insert the macOS hash line after the Windows hash line.

    Falls back to appending at the end of the body if the marker
    is not found - that way an upstream change to the body format
    cannot silently drop the macOS hash from the release notes.
    """
    insertion = f"**macOS SHA-256:** `{sha256}` ({dmg_name})\n"

    out_lines: list[str] = []
    inserted = False
    for line in body.splitlines(keepends=True):
        out_lines.append(line)
        if not inserted and WINDOWS_MARKER in line:
            if not line.endswith("\n"):
                out_lines.append("\n")
            out_lines.append(insertion)
            inserted = True

    if not inserted:
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines.append("\n")
        out_lines.append("\n" + insertion)

    return "".join(out_lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha256", required=True, help="DMG hex SHA-256.")
    parser.add_argument(
        "--dmg-name",
        required=True,
        help="Filename of the DMG as uploaded to the Release.",
    )
    args = parser.parse_args(argv)

    body = sys.stdin.read()
    sys.stdout.write(splice(body, sha256=args.sha256, dmg_name=args.dmg_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
