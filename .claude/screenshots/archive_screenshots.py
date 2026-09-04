#!/usr/bin/env python3
"""
Archives old files out of a project's .claude/screenshots/ directory once it
exceeds a cap, so it doesn't silently grow past a chat window's own
screenshot-attachment limit (20) before anyone notices.

This exists because prompts/10_screenshot-capture.md's Step 6.5 previously
asked an agent to count files and archive "if more than ~15" by hand
mid-session -- reliable in principle, easy to skip under time pressure. This
script makes the count-and-archive action itself mechanical instead of
aspirational (see the pipeline repo's PIPELINE_NEXT_ITERATION_ANALYSIS.md
v7.0, Finding F-6).

Usage (run from the project root, where .claude/ lives):
    python .claude/screenshots/archive_screenshots.py
    python .claude/screenshots/archive_screenshots.py --cap 15 --dir .claude/screenshots

Behavior: if the number of files directly inside the target directory (not
counting this script itself or existing archive-*/ subfolders) exceeds --cap,
moves the oldest files (by modification time) into a new
archive-<YYYYMMDD-HHMMSS>/ subfolder, keeping exactly --cap files active.

Never touches ./portfolio-screenshots/ -- that's Step 10's final deliverable,
a different directory with a different purpose (see
docs/claude-directory-spec.md in the pipeline repo).

Exit code 0 = no action needed or archive succeeded, 1 = target directory missing.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

SELF_NAME = "archive_screenshots.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir", default=".claude/screenshots",
        help="Directory to cap (default: .claude/screenshots)",
    )
    parser.add_argument(
        "--cap", type=int, default=15,
        help="Max active files before archiving (default: 15)",
    )
    args = parser.parse_args()

    target = Path(args.dir)
    if not target.exists():
        print(f"ERROR: {target} not found -- run this from the project root", file=sys.stderr)
        return 1

    files = sorted(
        (p for p in target.iterdir() if p.is_file() and p.name != SELF_NAME),
        key=lambda p: p.stat().st_mtime,
    )

    if len(files) <= args.cap:
        print(f"{target}: {len(files)} file(s), at or under cap ({args.cap}) -- no action needed.")
        return 0

    overflow = files[: len(files) - args.cap]
    archive_dir = target / f"archive-{datetime.now():%Y%m%d-%H%M%S}"
    archive_dir.mkdir()
    for path in overflow:
        path.rename(archive_dir / path.name)

    print(
        f"{target}: {len(files)} file(s) exceeded cap ({args.cap}) -- archived "
        f"{len(overflow)} oldest file(s) to {archive_dir}, {args.cap} remain active."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
