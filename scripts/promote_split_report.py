#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

SPLIT_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)
PROD_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)


def latest_split_report(split_dir: Path) -> Path:
    candidates: list[tuple[str, int, Path]] = []
    for path in split_dir.glob("weekly_fx_review_*.md"):
        match = SPLIT_RE.fullmatch(path.name)
        if not match:
            continue
        candidates.append((match.group(1), int(match.group(2) or "0"), path))
    if not candidates:
        raise FileNotFoundError(f"No split reports found in {split_dir}")
    candidates.sort(key=lambda row: (row[0], row[1]))
    return candidates[-1][2]


def next_prod_name(output_dir: Path, yymmdd: str) -> str:
    highest = 0
    for path in output_dir.glob(f"weekly_fx_review_{yymmdd}*.md"):
        match = PROD_RE.fullmatch(path.name)
        if not match or match.group(1) != yymmdd:
            continue
        highest = max(highest, int(match.group(2) or "0"))
    next_version = highest + 1 if highest else 1
    return f"weekly_fx_review_{yymmdd}_{next_version:02d}.md"


def promote(split_dir: Path, output_dir: Path, source_name: str | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = split_dir / source_name if source_name else latest_split_report(split_dir)
    if not source.exists():
        raise FileNotFoundError(f"Split report not found: {source}")
    match = SPLIT_RE.fullmatch(source.name)
    if not match:
        raise RuntimeError(f"Unexpected split report name: {source.name}")
    yymmdd = match.group(1)
    destination = output_dir / next_prod_name(output_dir, yymmdd)
    shutil.copy2(source, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote the latest split FX report into output/ for delivery.")
    parser.add_argument("--split-dir", default="output_split_test", help="Directory containing split test reports")
    parser.add_argument("--output-dir", default="output", help="Directory where delivery-ready FX reports live")
    parser.add_argument("--source-name", default=None, help="Specific split report filename to promote")
    args = parser.parse_args()

    promoted = promote(Path(args.split_dir), Path(args.output_dir), args.source_name)
    print(f"PROMOTE_OK | source_dir={args.split_dir} | promoted={promoted.as_posix()}")


if __name__ == "__main__":
    main()
