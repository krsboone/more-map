#!/usr/bin/env python3
"""
more_map.py — Portrait of a human-AI collaboration

Reads a More Protocol directory and produces a portrait of the collaboration:
session timeline, handoff map, topic threads, tone distribution.

Usage:
    python3 more_map.py
    python3 more_map.py --more /path/to/more/
    python3 more_map.py --no-color
"""

import argparse
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ── Optional dependencies ──────────────────────────────────────────────────────

try:
    import yaml
except ImportError:
    print("Error: PyYAML required.  pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box as rich_box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class Session:
    date: date
    title: str
    tone: str
    built: str
    mattered: str
    carry_forward: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Handoff:
    id: str
    status: str
    subject: str
    thread: str
    tags: list[str]
    created: Optional[date]
    updated: Optional[date]


# ── Parsing ────────────────────────────────────────────────────────────────────

_FM_RE   = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
_BOLD_RE = re.compile(r'\*\*([^*]+):\*\*\s*(.*?)(?=\n+\*\*|\Z)', re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"Warning: YAML parse error in frontmatter: {e}", file=sys.stderr)
        data = {}
    return data, text[m.end():]


def _parse_sections(body: str) -> dict[str, str]:
    """Extract ## Heading → content blocks."""
    sections: dict[str, str] = {}
    current: Optional[str] = None
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith('## '):
            if current is not None:
                sections[current] = '\n'.join(lines).strip()
            current = line[3:].strip()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = '\n'.join(lines).strip()
    return sections


def _parse_bold_fields(body: str) -> dict[str, str]:
    """Extract **Field:** value pairs from old-format journal entries."""
    return {m.group(1).strip(): m.group(2).strip() for m in _BOLD_RE.finditer(body)}


def _to_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), '%Y-%m-%d').date()
    except ValueError:
        return None


def load_sessions(more_path: Path) -> list[Session]:
    journal_dir = more_path / 'journal'
    if not journal_dir.exists():
        return []
    sessions = []
    for f in sorted(journal_dir.glob('*.md')):
        text = f.read_text()
        fm, body = _parse_frontmatter(text)
        session_date = _to_date(fm.get('date') or fm.get('created'))
        if not session_date:
            continue
        title = str(fm.get('session') or fm.get('subject', ''))
        tags  = list(fm.get('tags') or [])

        # New format: ## Section headings; old format: **Bold:** fields
        sections = _parse_sections(body)
        if sections:
            tone    = sections.get('Tone', '')
            built   = sections.get('What we built', '')
            mattered = sections.get('What mattered beyond the work',
                       sections.get('What mattered', ''))
            carry   = sections.get('Something to carry forward', '')
        else:
            bold    = _parse_bold_fields(body)
            tone    = bold.get('Tone', '')
            built   = bold.get('What we built', '')
            mattered = bold.get('What mattered', '')
            carry   = bold.get('Something to carry forward', '')

        sessions.append(Session(
            date=session_date, title=title, tone=tone,
            built=built, mattered=mattered, carry_forward=carry, tags=tags,
        ))
    return sessions


def load_handoffs(more_path: Path) -> list[Handoff]:
    handoff_dir = more_path / 'handoff'
    if not handoff_dir.exists():
        return []
    handoffs = []
    for f in sorted(handoff_dir.glob('*.md')):
        fm, _ = _parse_frontmatter(f.read_text())
        if not fm:
            continue
        handoffs.append(Handoff(
            id=str(fm.get('id', f.stem)),
            status=str(fm.get('status', 'unknown')),
            subject=str(fm.get('subject', '')),
            thread=str(fm.get('thread', '')),
            tags=list(fm.get('tags') or []),
            created=_to_date(fm.get('created')),
            updated=_to_date(fm.get('updated')),
        ))
    return handoffs


# ── Rendering helpers ──────────────────────────────────────────────────────────

def _first_line(text: str, max_len: int = 72) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return (line[:max_len] + '…') if len(line) > max_len else line
    return ''


def _bar(n: int, max_n: int, width: int = 18) -> str:
    filled = round(n / max_n * width) if max_n else 0
    return '█' * filled + '░' * (width - filled)


def _topic_counts(sessions: list[Session], handoffs: list[Handoff]) -> Counter:
    c: Counter = Counter()
    for s in sessions:
        c.update(s.tags)
    for h in handoffs:
        c.update(h.tags)
    # strip generic tags that don't reveal topic shape
    for noise in ('journal', 'handoff', 'active', 'confirmed', 'ai'):
        c.pop(noise, None)
    return c


# ── Plain-text output ──────────────────────────────────────────────────────────

def _plain(sessions: list[Session], handoffs: list[Handoff]) -> None:
    W = 70
    span = f"{sessions[0].date}  →  {sessions[-1].date}" if sessions else "–"

    print('━' * W)
    print("  more-map · collaboration portrait")
    print(f"  {len(sessions)} sessions · {len(handoffs)} handoffs · {span}")
    print('━' * W)

    # Timeline
    print("\n  SESSION TIMELINE\n")
    for s in sessions:
        print(f"  {s.date}  {_first_line(s.tone, 55)}")
        built = _first_line(s.built, 60)
        if built:
            print(f"             ↳  {built}")

    # Handoffs
    print("\n  HANDOFFS\n")
    by_status: dict[str, list[Handoff]] = {}
    for h in handoffs:
        by_status.setdefault(h.status, []).append(h)
    for status in ('active', 'partial', 'complete', 'archived', 'unknown'):
        group = by_status.get(status, [])
        if not group:
            continue
        print(f"  {status.upper()}  ({len(group)})")
        for h in group:
            subj = (h.subject[:60] + '…') if len(h.subject) > 60 else h.subject
            print(f"    ·  {h.id:<30}  {subj}")
        print()

    # Topics
    counts = _topic_counts(sessions, handoffs)
    if counts:
        print("  TOPIC THREADS\n")
        max_n = counts.most_common(1)[0][1]
        for tag, n in counts.most_common(18):
            print(f"  {tag:<24}  {_bar(n, max_n)}  {n}")

    # Tone strip
    print("\n\n  TONE OVER TIME\n")
    for s in sessions:
        print(f"  {s.date}  {_first_line(s.tone, 58)}")

    print()
    print('━' * W)


# ── Rich output ────────────────────────────────────────────────────────────────

def _rich(sessions: list[Session], handoffs: list[Handoff]) -> None:
    console = Console()
    span = f"{sessions[0].date}  →  {sessions[-1].date}" if sessions else "–"

    console.rule(style="dim")
    console.print(f"[bold]  more-map[/bold] [dim]· collaboration portrait[/dim]")
    console.print(f"  [dim]{len(sessions)} sessions · {len(handoffs)} handoffs · {span}[/dim]")
    console.rule(style="dim")

    # Timeline
    console.print()
    console.print("  [bold]SESSION TIMELINE[/bold]\n")
    t = Table(box=None, padding=(0, 2), show_header=False)
    t.add_column(style="dim cyan", no_wrap=True, width=12)
    t.add_column(no_wrap=False)
    for s in sessions:
        tone  = _first_line(s.tone, 62)
        built = _first_line(s.built, 62)
        cell  = tone + (f"\n[dim]  ↳  {built}[/dim]" if built else "")
        t.add_row(str(s.date), cell)
    console.print(t)

    # Handoffs
    console.print()
    console.print("  [bold]HANDOFFS[/bold]")
    by_status: dict[str, list[Handoff]] = {}
    for h in handoffs:
        by_status.setdefault(h.status, []).append(h)
    STATUS_COLOR = {'active': 'green', 'partial': 'yellow',
                    'complete': 'dim',  'archived': 'dim'}
    for status in ('active', 'partial', 'complete', 'archived', 'unknown'):
        group = by_status.get(status, [])
        if not group:
            continue
        color = STATUS_COLOR.get(status, 'white')
        console.print(f"\n  [{color}]{status.upper()}[/{color}]  ({len(group)})")
        for h in group:
            subj = (h.subject[:62] + '…') if len(h.subject) > 62 else h.subject
            console.print(f"    · [bold]{h.id}[/bold]  [dim]{subj}[/dim]")

    # Topics
    counts = _topic_counts(sessions, handoffs)
    if counts:
        console.print()
        console.print("\n  [bold]TOPIC THREADS[/bold]\n")
        max_n = counts.most_common(1)[0][1]
        t = Table(box=None, padding=(0, 1), show_header=False)
        t.add_column(style="bold", width=26)
        t.add_column(width=20)
        t.add_column(justify="right", style="dim")
        for tag, n in counts.most_common(18):
            t.add_row(tag, _bar(n, max_n), str(n))
        console.print(t)

    # Tone strip
    console.print()
    console.print("  [bold]TONE OVER TIME[/bold]\n")
    t = Table(box=None, padding=(0, 2), show_header=False)
    t.add_column(style="dim cyan", no_wrap=True, width=12)
    t.add_column()
    for s in sessions:
        t.add_row(str(s.date), _first_line(s.tone, 60))
    console.print(t)

    console.print()
    console.rule(style="dim")


# ── Entry point ────────────────────────────────────────────────────────────────

_DEFAULT_MORE = os.environ.get('MORE_PATH', str(Path.home() / 'more'))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="more-map — portrait of a human-AI collaboration")
    parser.add_argument(
        '--more',
        default=_DEFAULT_MORE,
        metavar='PATH',
        help="Path to More Protocol directory "
             "(default: $MORE_PATH or ~/more)",
    )
    parser.add_argument(
        '--no-color', action='store_true',
        help="Plain text output — no rich formatting",
    )
    args = parser.parse_args()

    more_path = Path(args.more).expanduser().resolve()
    if not more_path.exists():
        print(f"Error: directory not found: {more_path}", file=sys.stderr)
        print(f"  Set MORE_PATH or pass --more /path/to/more", file=sys.stderr)
        sys.exit(1)

    sessions = load_sessions(more_path)
    handoffs = load_handoffs(more_path)

    if HAS_RICH and not args.no_color:
        _rich(sessions, handoffs)
    else:
        _plain(sessions, handoffs)


if __name__ == '__main__':
    main()
