#!/usr/bin/env python3

"""Derive package version from git tag for CI publishing."""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


LOGGER = logging.getLogger(__name__)
TAG_PATTERN = re.compile(r"^v(?P<date>\d{8})\.(?P<sequence>[1-9]\d*)$")
VERSION_LINE_PATTERN = re.compile(r'(?m)^version = ".*"$')


@dataclass(frozen=True)
class ParsedTag:
    """Parsed release tag fields.

    Attributes:
        date: Release date in YYYYMMDD.
        sequence: Release sequence for the same date.
    """

    date: str
    sequence: int

    @property
    def pep440_version(self) -> str:
        """Build PEP440 version for package publishing.

        Returns:
            str: PEP440-compliant version string.
        """
        return f"{self.date}.{self.sequence}"


def parse_release_tag(tag: str) -> ParsedTag:
    """Parse release tag into structured version fields.

    Args:
        tag: Git tag string, supports `vYYYYMMDD.N`.

    Returns:
        ParsedTag: Structured tag fields.

    Raises:
        ValueError: If tag format is unsupported.
    """
    matched = TAG_PATTERN.match(tag)
    if matched is not None:
        date_value = matched.group("date")
        _validate_date(date_value)
        return ParsedTag(
            date=date_value,
            sequence=int(matched.group("sequence")),
        )

    raise ValueError(f"unsupported tag format: {tag}")


def _validate_date(date_value: str) -> None:
    """Validate YYYYMMDD date string.

    Args:
        date_value: Date suffix from tag.

    Raises:
        ValueError: If date string is not a valid calendar date.
    """
    try:
        datetime.strptime(date_value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid date in tag: {date_value}") from exc


def update_pyproject_version(pyproject_path: Path, version: str) -> None:
    """Update project version field in pyproject.toml.

    Args:
        pyproject_path: pyproject.toml path.
        version: Target version string.

    Raises:
        ValueError: If version field is missing.
    """
    content = pyproject_path.read_text(encoding="utf-8")
    updated, count = VERSION_LINE_PATTERN.subn(
        f'version = "{version}"', content, count=1
    )
    if count != 1:
        raise ValueError("failed to locate version field in pyproject.toml")
    pyproject_path.write_text(updated, encoding="utf-8")


def append_github_env(env_path: Path, version: str) -> None:
    """Append package version into GitHub Actions environment file.

    Args:
        env_path: Path to GitHub environment file.
        version: Version string to export.
    """
    with env_path.open("a", encoding="utf-8") as env_file:
        env_file.write(f"PACKAGE_VERSION={version}\n")


def build_parser() -> argparse.ArgumentParser:
    """Build command-line parser for the script.

    Returns:
        argparse.ArgumentParser: Argument parser instance.
    """
    parser = argparse.ArgumentParser(
        description="Derive package version from release tag and sync pyproject.toml."
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Release tag, e.g. v20260314.1.",
    )
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml.",
    )
    parser.add_argument(
        "--github-env",
        default=None,
        help="Optional path to $GITHUB_ENV.",
    )
    return parser


def main() -> int:
    """Run command-line entrypoint.

    Returns:
        int: Process exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args()

    parsed_tag = parse_release_tag(args.tag)
    target_version = parsed_tag.pep440_version

    update_pyproject_version(Path(args.pyproject), target_version)
    LOGGER.info("Set package version to %s from tag %s", target_version, args.tag)

    if args.github_env is not None:
        append_github_env(Path(args.github_env), target_version)
        LOGGER.info("Exported PACKAGE_VERSION to %s", args.github_env)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
