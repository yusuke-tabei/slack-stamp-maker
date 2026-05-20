#!/usr/bin/env python3
"""Slice a portrait into a 3x3 (9-tile) giant Slack emoji.

Usage:
    python make_big3x3.py <image> <name> [--out DIR]

Each tile is 128x128. Registered as 9 custom emoji and arranged in a message,
they render as one big 384x384 picture. A layout note is written alongside the
tiles with the exact emoji arrangement to paste into Slack.
"""
import argparse
from pathlib import Path

from PIL import Image

TILE = 128
GRID = 3
FULL = TILE * GRID  # 384


def build(src_path: str, name: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Image.open(src_path).convert("RGBA")

    # Center square crop so the face fills all 9 tiles
    w, h = src.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    square = src.crop((left, top, left + side, top + side)).resize((FULL, FULL), Image.LANCZOS)

    for r in range(GRID):
        for c in range(GRID):
            tile = square.crop((c * TILE, r * TILE, (c + 1) * TILE, (r + 1) * TILE))
            tile.save(out_dir / f"{name}_big_r{r + 1}c{c + 1}.png")

    layout = "Paste these three lines (with line breaks) into Slack to render the giant image:\n\n"
    for r in range(GRID):
        layout += "".join(f":{name}_big_r{r + 1}c{c + 1}:" for c in range(GRID)) + "\n"
    layout += "\nRegister each tile as a custom emoji under the name above first.\n"
    (out_dir / f"{name}_big3x3_layout.txt").write_text(layout)
    print(f"{name}: 9 tiles + layout note written to {out_dir}/")


def main():
    ap = argparse.ArgumentParser(description="Slice a portrait into a 3x3 giant Slack emoji.")
    ap.add_argument("image", help="source portrait image")
    ap.add_argument("name", help="emoji base name, e.g. 'alice'")
    ap.add_argument("--out", default=None, help="output directory (default: ./<name>_stamps)")
    args = ap.parse_args()
    out_dir = Path(args.out) if args.out else Path.cwd() / f"{args.name}_stamps"
    build(args.image, args.name, out_dir)


if __name__ == "__main__":
    main()
