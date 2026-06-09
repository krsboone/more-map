# more-map

A tool for reading a [More Protocol](https://github.com/krsboone/more) memory store and producing a portrait of the collaboration it holds.

## What it does

Parses journal entries, handoff files, and tags from a More Protocol directory and renders:

- **Session timeline** — dates, tone, and what was built each session
- **Handoffs** — grouped by status (active / partial / complete / archived)
- **Topic threads** — tags ranked by frequency across sessions and handoffs
- **Tone over time** — the emotional texture of the collaboration as a chronological strip

Output uses [rich](https://github.com/Textualize/rich) formatting by default; falls back to plain text with `--no-color`.

## Requirements

Requires a directory conforming to the **[More Protocol](https://github.com/krsboone/more)** spec. The tool reads:

- `journal/*.md` — session entries with frontmatter (`date`, `tags`) and section headings (`## Tone`, `## What we built`, etc.)
- `handoff/*.md` — handoff files with frontmatter (`id`, `status`, `subject`, `tags`, `created`, `updated`)

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
