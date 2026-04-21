#!/usr/bin/env python3
"""
Generate color-grading LUT (.cube) files for ReelForge AI assembly worker.

Produces four 17x17x17 LUTs — 4,913 RGB triplets each — in the Adobe/Resolve
CUBE format that FFmpeg's `lut3d` filter accepts natively.

Usage:
    python3 scripts/generate_luts.py                  # writes to /app/luts/
    LUT_DIR=./luts python3 scripts/generate_luts.py   # custom output dir

Called automatically during the workers Docker image build.
"""

import os

# 17×17×17 is the smallest size that gives smooth gradations with no banding.
# 33×33×33 would be higher quality but tripling the file size is unnecessary.
SIZE = 17
STEP = 1.0 / (SIZE - 1)


def clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


# ---------------------------------------------------------------------------
# Color transforms
# Each function receives linear [0,1] RGB and returns transformed [0,1] RGB.
# ---------------------------------------------------------------------------

def lut_moody(r: float, g: float, b: float):
    """
    Desaturated, slightly blue-shadowed, matte blacks.
    Signature: film-noir / editorial mood.
    """
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Desaturate 15 % toward luminance
    r2 = r * 0.85 + lum * 0.15
    g2 = g * 0.88 + lum * 0.12
    b2 = b * 0.92 + lum * 0.08

    # Blue tint fades into shadows — zero effect in highlights
    shadow = max(0.0, 1.0 - min(1.0, (r + g + b) / 1.5))
    b2 += shadow * 0.045
    g2 += shadow * 0.012

    # Matte-black lift: crush pure white a touch, float pure black
    r2 = r2 * 0.91 + 0.025
    g2 = g2 * 0.92 + 0.022
    b2 = b2 * 0.94 + 0.030

    return clamp(r2), clamp(g2), clamp(b2)


def lut_warm_cinematic(r: float, g: float, b: float):
    """
    Teal-orange look: warm golden mids/shadows, cool teal highlights.
    The industry-standard "blockbuster" grade.
    """
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Orange push in shadows/mids
    r2 = r * 1.07 + 0.030
    g2 = g * 0.97 + 0.012
    b2 = b * 0.84 + 0.020

    # Teal shift in highlights (classic complementary contrast)
    hi = max(0.0, lum - 0.55) / 0.45
    r2 -= hi * 0.050
    g2 += hi * 0.018
    b2 += hi * 0.055

    # Filmic toe — lift blacks, slightly roll off highlights
    r2 = r2 * 0.93 + 0.040
    g2 = g2 * 0.94 + 0.030
    b2 = b2 * 0.95 + 0.022

    return clamp(r2), clamp(g2), clamp(b2)


def lut_bright_pop(r: float, g: float, b: float):
    """
    +1/3 stop exposure, +25% saturation boost, vivid punchy colours.
    Ideal for travel, food, lifestyle niches.
    """
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Boost saturation 25 % (blues boosted an extra 5 % for sky/water pop)
    r2 = lum + (r - lum) * 1.25
    g2 = lum + (g - lum) * 1.25
    b2 = lum + (b - lum) * 1.32

    # +1/3 stop (≈ ×1.08 in linear light)
    r2 *= 1.08
    g2 *= 1.07
    b2 *= 1.06

    # Gentle highlight protection — prevent blowout
    def protect(v):
        if v > 0.85:
            excess = v - 0.85
            return 0.85 + excess * 0.45
        return v

    return clamp(protect(r2)), clamp(protect(g2)), clamp(protect(b2))


def lut_dark_dramatic(r: float, g: float, b: float):
    """
    Deep S-curve shadows, crushed blacks, slightly cooled highlights.
    For fashion, music, dark-aesthetic niches.
    """
    def s_curve(v: float) -> float:
        """Smooth piecewise S-curve: deepens shadows, clips highlights."""
        if v <= 0.0:
            return 0.0
        if v >= 1.0:
            return 1.0
        if v < 0.5:
            return 2.0 * v * v
        return 1.0 - 2.0 * (1.0 - v) ** 2

    r2 = s_curve(r)
    g2 = s_curve(g)
    b2 = s_curve(b)

    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Cool the shadows: pull red down, push blue up
    shadow = max(0.0, 1.0 - lum * 3.0)
    r2 -= shadow * 0.055
    b2 += shadow * 0.040

    # Slightly desaturate highlights to avoid neon clipping
    hi = max(0.0, lum - 0.72) / 0.28
    lum2 = 0.299 * r2 + 0.587 * g2 + 0.114 * b2
    mix = hi * 0.18
    r2 = r2 * (1 - mix) + lum2 * mix
    g2 = g2 * (1 - mix) + lum2 * mix
    b2 = b2 * (1 - mix) + lum2 * mix

    return clamp(r2), clamp(g2), clamp(b2)


# ---------------------------------------------------------------------------
# CUBE file writer
# ---------------------------------------------------------------------------

LUTS = {
    "moody": lut_moody,
    "warm_cinematic": lut_warm_cinematic,
    "bright_pop": lut_bright_pop,
    "dark_dramatic": lut_dark_dramatic,
}

# The CUBE spec iterates: R (fastest) → G → B (slowest).
# FFmpeg's lut3d filter follows the same convention.


def write_cube(name: str, transform, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{name}.cube")

    with open(path, "w") as fh:
        fh.write(f'TITLE "{name}"\n')
        fh.write(f"LUT_3D_SIZE {SIZE}\n")
        fh.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        fh.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        fh.write("\n")

        for bi in range(SIZE):
            for gi in range(SIZE):
                for ri in range(SIZE):
                    r_in = ri * STEP
                    g_in = gi * STEP
                    b_in = bi * STEP
                    ro, go, bo = transform(r_in, g_in, b_in)
                    fh.write(f"{ro:.6f} {go:.6f} {bo:.6f}\n")

    entries = SIZE ** 3
    print(f"  ✓  {path}  ({entries} entries)")


def main() -> None:
    output_dir = os.environ.get("LUT_DIR", "/app/luts")
    print(f"Generating {len(LUTS)} LUTs → {output_dir}/")
    for name, fn in LUTS.items():
        write_cube(name, fn, output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
