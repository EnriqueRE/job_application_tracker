"""Parse JobTrack's Markdown Job Description files and match them strictly to Applications.

JobTrack wrote one file per Application from this template (CRLF line endings)::

    # {role} — {organization}

    - Application ID: {id}
    - Status: {status}
    - Vacancy URL: {url}
    - Captured: {date}

    ## Job description

    {body}

Application IDs are not unique across files, so a file attaches to an Application only when
both its ``Application ID`` header and its heading match that Application. The ``Status``
header and the directory are stale in practice and are ignored.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

AGGREGATE_FILES = frozenset({"no_response.md", "rejections.md"})
"""Top-level files that concatenate many per-Application files; never imported."""

_SECTION = re.compile(r"^## Job description[ \t]*$", re.MULTILINE)
_HEADING = re.compile(r"^# (.*)$", re.MULTILINE)
_APPLICATION_ID = re.compile(r"^- Application ID:[ \t]*(\d+)[ \t]*$", re.MULTILINE)


@dataclass(frozen=True)
class JobDescriptionFile:
    path: str
    """Relative to the Markdown directory, with forward slashes."""
    jobtrack_application_id: int
    heading: str
    body: str | None
    """The text under ``## Job description``; None when it is empty."""


@dataclass(frozen=True)
class UnmatchedFile:
    path: str
    reason: str
    """``unparseable``, ``no_application_with_id``, ``heading_mismatch`` or ``ambiguous``."""
    detail: str


@dataclass(frozen=True)
class MatchResult:
    matches: dict[int, JobDescriptionFile]
    """JobTrack Application id -> the one file that matched it."""
    unmatched: list[UnmatchedFile]


def expected_heading(role: str, organization: str) -> str:
    return f"{role.strip()} — {organization.strip()}"


def parse(path: str, text: str) -> JobDescriptionFile | UnmatchedFile:
    text = text.replace("\r\n", "\n")
    section = _SECTION.search(text)
    if section is None:
        return UnmatchedFile(path, "unparseable", "no '## Job description' section")
    header = text[: section.start()]
    heading = _HEADING.search(header)
    if heading is None:
        return UnmatchedFile(path, "unparseable", "no '# Role — Organization' heading")
    application_id = _APPLICATION_ID.search(header)
    if application_id is None:
        return UnmatchedFile(path, "unparseable", "no 'Application ID' header")
    return JobDescriptionFile(
        path=path,
        jobtrack_application_id=int(application_id.group(1)),
        heading=heading.group(1).strip(),
        body=_body(text[section.end() :]),
    )


def _body(text: str) -> str | None:
    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    body = "\n".join(lines).rstrip()
    return body or None


def find_files(markdown_dir: Path) -> list[Path]:
    if not markdown_dir.is_dir():
        raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")
    return sorted(
        path
        for path in markdown_dir.rglob("*.md")
        if path.is_file() and path.relative_to(markdown_dir).as_posix() not in AGGREGATE_FILES
    )


def match(markdown_dir: Path, applications: dict[int, tuple[str, str]]) -> MatchResult:
    """Match every file under ``markdown_dir`` to ``applications`` (id -> (role, organization))."""
    unmatched: list[UnmatchedFile] = []
    candidates: defaultdict[int, list[JobDescriptionFile]] = defaultdict(list)
    for file in find_files(markdown_dir):
        relative = file.relative_to(markdown_dir).as_posix()
        parsed = parse(relative, file.read_text(encoding="utf-8"))
        if isinstance(parsed, UnmatchedFile):
            unmatched.append(parsed)
            continue
        application_id = parsed.jobtrack_application_id
        if application_id not in applications:
            unmatched.append(
                UnmatchedFile(
                    relative,
                    "no_application_with_id",
                    f"no Application {application_id} in the JobTrack database",
                )
            )
            continue
        wanted = expected_heading(*applications[application_id])
        if parsed.heading != wanted:
            unmatched.append(
                UnmatchedFile(
                    relative,
                    "heading_mismatch",
                    f"Application {application_id} is '{wanted}', "
                    f"file heading is '{parsed.heading}'",
                )
            )
            continue
        candidates[application_id].append(parsed)

    matches: dict[int, JobDescriptionFile] = {}
    for application_id, files in candidates.items():
        if len(files) == 1:
            matches[application_id] = files[0]
            continue
        others = ", ".join(f.path for f in files)
        unmatched.extend(
            UnmatchedFile(
                f.path,
                "ambiguous",
                f"{len(files)} files match Application {application_id}: {others}",
            )
            for f in files
        )
    return MatchResult(matches=matches, unmatched=unmatched)
