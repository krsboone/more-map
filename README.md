# more-map

A tool for reading a [More Protocol](https://github.com/krsboone/more-protocol) memory store and producing a portrait of the collaboration it holds.

## What it does

Parses journal entries, handoffs, constraints, experience memories, and tags
from a More Protocol directory and renders:

- **Session timeline** — dates, tone, and what was built each session
- **Handoffs** — grouped by status (active / partial / resolved / superseded / expired / deprecated), with a staleness flag for `active`/`partial` handoffs that haven't been touched in a while
- **Constraints** — binding rules currently in force, with scope (global / project) and any exemptions
- **Growth** — a timeline of `experience` memories, marking shifts in understanding over time
- **Topic threads** — tags ranked by frequency across sessions, handoffs, constraints, and experience memories
- **Tone over time** — the emotional texture of the collaboration as a chronological strip
- **Index health** — `MEMORY.md` line count against the spec's recommended 200-line ceiling

Output uses [rich](https://github.com/Textualize/rich) formatting by default; falls back to plain text with `--no-color`.

## Requirements

Requires a directory conforming to the **[More Protocol](https://github.com/krsboone/more-protocol)** spec. The tool reads:

- `MEMORY.md` — the index, for a line-count health check
- `journal/*.md` — session entries with frontmatter (`date`, `tags`) and section headings (`## Tone`, `## What we built`, etc.)
- `handoff/*.md` — handoff files with frontmatter (`id`, `status`, `subject`, `tags`, `created`, `updated`, `expires_after`)
- `constraints/*.md` — constraint files with frontmatter (`id`, `subject`, `scope`, `project`, `exempt`, `tags`)
- `experience/*.md` — experience files with frontmatter (`id`, `subject`, `created`, `tags`)

Without a More Protocol store there is nothing to read.

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `pyyaml`, `rich` (optional but recommended).

## Usage

```bash
# Uses $MORE_PATH or ~/more by default
python3 more_map.py

# Point at a specific More Protocol directory
python3 more_map.py --more /path/to/more

# Plain text output
python3 more_map.py --no-color
```

The `MORE_PATH` environment variable can be set to avoid passing `--more` each time.
