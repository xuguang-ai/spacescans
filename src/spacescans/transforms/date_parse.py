"""Filename/field to date parsing primitives."""
from __future__ import annotations
import datetime
import re
from pathlib import Path
from typing import Callable


def parse_date_from_filename(filename: str, *, pattern: str, date_format: str | None = None) -> datetime.date:
    m = re.search(pattern, str(filename))
    if not m:
        raise ValueError(f"Pattern {pattern!r} did not match filename {filename!r}")
    date_str = m.group("date")
    fmt = date_format or "%Y%m%d"
    return datetime.datetime.strptime(date_str, fmt).date()


def parse_date_range_from_filename(filename: str, *, pattern: str, date_format: str | None = None) -> tuple[datetime.date, datetime.date]:
    m = re.search(pattern, str(filename))
    if not m:
        raise ValueError(f"Pattern {pattern!r} did not match filename {filename!r}")
    fmt = date_format or "%Y%j"
    start = datetime.datetime.strptime(m.group("start"), fmt).date()
    end = datetime.datetime.strptime(m.group("end"), fmt).date()
    return start, end


def discover_files_with_dates(base_dir: str | Path, *, glob_pattern: str, date_parser: Callable[[str], datetime.date], year_range: tuple[int, int] | None = None) -> list[tuple[Path, datetime.date]]:
    base = Path(base_dir)
    results = []
    for path in sorted(base.glob(glob_pattern)):
        try:
            d = date_parser(path.name)
        except (ValueError, AttributeError):
            continue
        if year_range and not (year_range[0] <= d.year <= year_range[1]):
            continue
        results.append((path, d))
    return sorted(results, key=lambda x: x[1])
