# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Monospace adaptation of the Audiowide font for use as a coding font. The original Audiowide is a proportional-width display font by Brian J. Bonislawsky (Astigmatic). This project converts it to a monospaced font suitable for terminals, editors, and tmux/powerline.

Licensed under SIL Open Font License (OFL).

## Repository Structure

- `audiowide-mono/` — The monospaced derivative
  - `Audiowide Mono-275.ufo/` — UFO source (Unified Font Object format, XML-based)
    - `glyphs/` — Individual glyph outlines as `.glif` XML files (~370 glyphs)
    - `fontinfo.plist` — Font metadata (ascender/descender, units-per-em=1024, etc.)
    - `contents.plist` — Glyph name to filename mapping
  - `Audiowide-Mono-*.ttf` — Compiled TrueType binaries (various versions)
  - `Audiowide-Mono-Latest.ttf` — Current release binary
- `audiowide-original/` — Upstream Audiowide-Regular.ttf for reference

## Key Constraints

- **All glyphs must be exactly 750 units wide** (`<advance width="750"/>`). This is critical for monospace correctness — VSCode and other editors will reject the font if widths vary.
- Glyph outlines use **quadratic curves** (`qcurve`), not cubic (`curve`).
- Includes powerline symbols and tmux support glyphs.

## Tools

Font editing is done with [FontForge](https://fontforge.org/). The UFO format is the source of truth; TTF files are compiled outputs.

To generate a new TTF from the UFO source, use FontForge's "Generate Fonts" feature or its Python scripting interface.
