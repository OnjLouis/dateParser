# Date Parser

Date Parser resolves plain-English date expressions and calendar dates into a concrete date.

## Quick Start

1. Press `NVDA+Alt+E` to open Date Parser.
2. Type a date expression (for example `tomorrow`, `next thu`, `5d`, `Mar 5`).
3. Press `Enter` to resolve it.
4. Copy results with `Ctrl+C`.

## Common Inputs

- Everyday words: `today`, `tomorrow`, `yesterday`
- Weekdays: `mon`, `tuesday`, `next thu`, `last wed`
- Relative offsets: `5d`, `2w from now`, `5y 4m 3w 2d ago`, `5y -4m +3w -2d`
- Counted weekdays: `25 Fri ago`, `-25Fri`, `3 Mondays prior`
- Calendar dates: `05/06/2026`, `1992-09-01`, `13 Apr 2026`, `5 jun 26`, `Mar 5`
- Boundary dates: `end of month`, `start of next year`

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `NVDA+Alt+E` | Open Date Parser input dialog |
| `Ctrl+C` | Copy selected result text |
| `Enter` | Close result dialog |
| `Escape` | Close result dialog |
| `F1` | Open help from the input or result dialog |

## Changes

- 1.0.4: Adds a dedicated Date Parser category in NVDA's Input Gestures dialog.

## Full Documentation

- Full reference and examples: [`source/doc/en/readme.html`](source/doc/en/readme.html)

## Source Code

- Extracted source for this build: [`source/`](source/)
- Main plugin: [`source/globalPlugins/dateParser.py`](source/globalPlugins/dateParser.py)

## Install

1. Download the `.nvda-addon` file from Releases.
2. In NVDA, open Add-on Manager and choose Install.
3. Select the file and restart NVDA when prompted.
