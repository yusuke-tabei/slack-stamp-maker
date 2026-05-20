#!/usr/bin/env python3
"""Turn a single portrait image into a set of animated Slack emoji GIFs.

Usage:
    python make_stamps.py <image> <name> [--out DIR]

Example:
    python make_stamps.py face.png alice --out ./out

Produces 14 looping GIFs (pulse, shake, vibrate, wobble, spin, rainbow_bg,
rainbow_tint, party, zoom, parrot, plus "hard" = bigger & faster variants),
each <=128KB and sized 128x128 so they work as Slack custom emoji.

Tip: a cut-out PNG with a transparent background looks cleanest. A regular
photo works too, but the whole rectangle (background included) will animate.
"""
import argparse
import math
import colorsys
from pathlib import Path

from PIL import Image

SIZE = 128  # Slack emoji recommended size


def build(src_path: str, name: str, out_dir: Path):
    src = Image.open(src_path).convert("RGBA")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Fit into SIZE x SIZE keeping aspect ratio
    w, h = src.size
    fit = SIZE / max(w, h)
    fitted = src.resize((max(1, int(w * fit)), max(1, int(h * fit))), Image.LANCZOS)

    def base(scale=1.0):
        bw, bh = fitted.size
        return fitted.resize((max(1, int(bw * scale)), max(1, int(bh * scale))), Image.LANCZOS)

    def canvas():
        return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    def paste_centered(cnv, img, dx=0, dy=0):
        x = (SIZE - img.width) // 2 + dx
        y = (SIZE - img.height) // 2 + dy
        cnv.alpha_composite(img, (x, y))
        return cnv

    def save_transparent_gif(frames, fname, duration_ms, num_colors=112):
        """Save RGBA frames as a transparent GIF, kept under Slack's 128KB limit."""
        pal_frames = []
        for f in frames:
            rgb = f.convert("RGB")
            q = rgb.quantize(colors=num_colors, method=Image.MEDIANCUT)
            alpha = f.split()[-1]
            mask = alpha.point(lambda a: 255 if a <= 128 else 0)
            q.paste(num_colors, mask)  # reserve index=num_colors for transparency
            pal_frames.append(q)
        path = out_dir / fname
        pal_frames[0].save(
            path, save_all=True, append_images=pal_frames[1:],
            duration=duration_ms, loop=0, disposal=2,
            transparency=num_colors, optimize=True,
        )
        print(f"  -> {fname}")

    def save_opaque_gif(frames, fname, duration_ms, num_colors=64):
        """Save filled-background frames (rainbow types) with color reduction."""
        rgb = [f.convert("RGB").quantize(colors=num_colors, method=Image.MEDIANCUT) for f in frames]
        path = out_dir / fname
        rgb[0].save(
            path, save_all=True, append_images=rgb[1:],
            duration=duration_ms, loop=0, optimize=True,
        )
        print(f"  -> {fname}")

    # 1) Pulse (scale in/out)
    def make_pulse():
        frames = []
        N = 16
        for i in range(N):
            t = i / N
            scale = 0.85 + 0.15 * (0.5 + 0.5 * math.sin(t * 2 * math.pi))
            frames.append(paste_centered(canvas(), base(scale)))
        save_transparent_gif(frames, f"{name}_pulse.gif", 70)

    # 2) Shake left-right
    def make_shake():
        frames = []
        N = 14
        img = base(0.92)
        for i in range(N):
            t = i / N
            dx = int(14 * math.sin(t * 2 * math.pi))
            frames.append(paste_centered(canvas(), img, dx=dx))
        save_transparent_gif(frames, f"{name}_shake.gif", 50)

    # 3) Vibrate
    def make_vibrate():
        import random
        random.seed(1)
        frames = []
        img = base(0.9)
        for _ in range(12):
            frames.append(paste_centered(canvas(), img, dx=random.randint(-6, 6), dy=random.randint(-6, 6)))
        save_transparent_gif(frames, f"{name}_vibrate.gif", 45)

    # 4) Wobble (tilt back and forth)
    def make_wobble():
        frames = []
        N = 16
        img = base(0.85)
        for i in range(N):
            angle = 18 * math.sin(i / N * 2 * math.pi)
            frames.append(paste_centered(canvas(), img.rotate(angle, resample=Image.BICUBIC, expand=True)))
        save_transparent_gif(frames, f"{name}_wobble.gif", 60)

    # 5) Spin (full rotation)
    def make_spin():
        frames = []
        N = 18
        img = base(0.82)
        for i in range(N):
            frames.append(paste_centered(canvas(), img.rotate(-360 * i / N, resample=Image.BICUBIC, expand=True)))
        save_transparent_gif(frames, f"{name}_spin.gif", 55)

    # 6) Rainbow background (saturation pulses through 0 so the plain photo shows once per loop)
    def make_rainbow_bg():
        frames = []
        N = 18
        img = base(0.92)
        for i in range(N):
            t = i / N
            sat = 0.85 * (0.5 - 0.5 * math.cos(t * 2 * math.pi))
            r, g, b = colorsys.hsv_to_rgb(t, sat, 1.0)
            bg = Image.new("RGBA", (SIZE, SIZE), (int(r * 255), int(g * 255), int(b * 255), 255))
            bg.alpha_composite(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2))
            frames.append(bg)
        save_opaque_gif(frames, f"{name}_rainbow_bg.gif", 80)

    # 7) Rainbow tint (color strength pulses to 0 so the original face shows once per loop)
    def make_rainbow_tint():
        frames = []
        N = 18
        img = base(0.92)
        alpha = img.split()[-1]
        for i in range(N):
            t = i / N
            strength = int(150 * (0.5 - 0.5 * math.cos(t * 2 * math.pi)))
            r, g, b = colorsys.hsv_to_rgb(t, 0.6, 1.0)
            tint = Image.new("RGBA", img.size, (int(r * 255), int(g * 255), int(b * 255), 255))
            colored = Image.composite(tint, img, Image.new("L", img.size, strength))
            colored.putalpha(alpha)
            frames.append(paste_centered(canvas(), colored))
        save_transparent_gif(frames, f"{name}_rainbow_tint.gif", 80, num_colors=80)

    # 8) Party (pulse + rainbow background)
    def make_party():
        frames = []
        N = 18
        for i in range(N):
            t = i / N
            scale = 0.8 + 0.18 * (0.5 + 0.5 * math.sin(t * 4 * math.pi))
            img = base(scale)
            sat = 0.85 * (0.5 - 0.5 * math.cos(t * 2 * math.pi))
            r, g, b = colorsys.hsv_to_rgb(t, sat, 1.0)
            bg = Image.new("RGBA", (SIZE, SIZE), (int(r * 255), int(g * 255), int(b * 255), 255))
            bg.alpha_composite(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2))
            frames.append(bg)
        save_opaque_gif(frames, f"{name}_party.gif", 70)

    # 9) Zoom (push in hard, up to 2.6x)
    def make_zoom():
        frames = []
        N = 16
        for i in range(N):
            t = i / N
            scale = 0.8 + 1.8 * (0.5 - 0.5 * math.cos(t * 2 * math.pi))
            frames.append(paste_centered(canvas(), base(scale)))
        save_transparent_gif(frames, f"{name}_zoom.gif", 65, num_colors=56)

    # 10) Party-parrot style: head bobs around while the background cycles rainbow
    def make_parrot(suffix="parrot", swing=11, lift=8, tilt_amt=14, squash_amt=0.10,
                    base_scale=0.9, duration=70):
        frames = []
        N = 10  # same frame count as the original party parrot
        for i in range(N):
            t = i / N
            p = t * 2 * math.pi
            dx = int(swing * math.sin(p))
            dy = int(-lift * math.cos(p)) + 4
            tilt = tilt_amt * math.sin(p)
            squash = 1.0 + squash_amt * math.cos(p)
            bimg = base(base_scale)
            bw, bh = bimg.size
            img = bimg.resize((int(bw / squash ** 0.5), int(bh * squash ** 0.5)), Image.LANCZOS)
            img = img.rotate(tilt, resample=Image.BICUBIC, expand=True)
            r, g, b = colorsys.hsv_to_rgb(t, 0.9, 1.0)
            bg = Image.new("RGBA", (SIZE, SIZE), (int(r * 255), int(g * 255), int(b * 255), 255))
            bg.alpha_composite(img, ((SIZE - img.width) // 2 + dx, (SIZE - img.height) // 2 + dy))
            frames.append(bg)
        save_opaque_gif(frames, f"{name}_{suffix}.gif", duration)

    # --- intense & fast variants ---

    def make_shake_hard():
        frames = []
        N = 12
        img = base(0.9)
        for i in range(N):
            t = i / N
            dx = int(30 * math.sin(t * 2 * math.pi))
            tilt = 8 * math.sin(t * 2 * math.pi)
            frames.append(paste_centered(canvas(), img.rotate(tilt, resample=Image.BICUBIC, expand=True), dx=dx))
        save_transparent_gif(frames, f"{name}_shake_hard.gif", 30)

    def make_vibrate_hard():
        import random
        random.seed(7)
        frames = []
        img = base(0.9)
        for _ in range(14):
            rot = img.rotate(random.uniform(-7, 7), resample=Image.BICUBIC, expand=True)
            frames.append(paste_centered(canvas(), rot, dx=random.randint(-16, 16), dy=random.randint(-16, 16)))
        save_transparent_gif(frames, f"{name}_vibrate_hard.gif", 28)

    def make_pulse_hard():
        frames = []
        N = 12
        for i in range(N):
            t = i / N
            scale = 0.8 + 0.35 * (0.5 + 0.5 * math.sin(t * 4 * math.pi))
            frames.append(paste_centered(canvas(), base(scale)))
        save_transparent_gif(frames, f"{name}_pulse_hard.gif", 40)

    print(f"Generating Slack stamp GIFs for '{name}'...")
    make_pulse()
    make_shake()
    make_vibrate()
    make_wobble()
    make_spin()
    make_rainbow_bg()
    make_rainbow_tint()
    make_party()
    make_zoom()
    make_parrot()
    make_shake_hard()
    make_vibrate_hard()
    make_pulse_hard()
    make_parrot("parrot_hard", swing=20, lift=14, tilt_amt=24, squash_amt=0.18,
                base_scale=0.88, duration=45)
    print(f"Done. Files written to {out_dir}/")


def main():
    ap = argparse.ArgumentParser(description="Make animated Slack emoji GIFs from a portrait.")
    ap.add_argument("image", help="source portrait image (PNG/JPG; transparent PNG looks best)")
    ap.add_argument("name", help="emoji base name, e.g. 'alice'")
    ap.add_argument("--out", default=None, help="output directory (default: ./<name>_stamps)")
    args = ap.parse_args()
    out_dir = Path(args.out) if args.out else Path.cwd() / f"{args.name}_stamps"
    build(args.image, args.name, out_dir)


if __name__ == "__main__":
    main()
