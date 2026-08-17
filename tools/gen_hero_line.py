"""Generate the hero trend line path, its arc length (for stroke-dasharray)
and the arrowhead polygon.

Points are given as percentages of the hero box; the SVG uses
viewBox="0 0 1200 825" with preserveAspectRatio="none", so percentages map
linearly onto viewBox units regardless of the hero's real aspect ratio.

Constraints the route has to respect (measured, not guessed):
  * the volume strip sits at y 86.5-88.9%, with items ending at x 64%
    and the last one starting at x 80.9% -- so the climb has to cross the
    strip band inside the x 65-80 corridor.
  * the low run stays below the strip with >=4% clearance.
"""
import math
import os

W, H = 1200.0, 825.0
# Low tension keeps the legs near-straight -- a stock chart reads as segments,
# not as a wave.
TENSION = 0.12

# The hero runs taller than the viewport -- on a short laptop the fold lands
# around 72% of the hero -- so the climb has to start early and to the LEFT to
# be seen at all. Measured constraints:
#   * volume strip band y 84.9-88.9 (varies by width); its first gap is
#     x 28-38.5 once every width is accounted for (the container
#     centres on wide screens, pushing the first item right).
#   * left text column occupies x 3.8-54 down to y 79.3, so the line stays
#     below y 82 until it is clear of it, and right of x 54 before rising
#     above the buttons (y 63.6).
PTS_PCT = [
    (2, 97), (10, 95), (18, 96.5), (24, 94),     # base run, below the strip
    (30, 90.5), (35, 83.5),                       # cross the band inside gap 1
    (41, 83.8), (47, 83.3),                       # flat through the corridor
    (53, 73), (56, 75.5),                         # clear of the text -- start climbing
    (62, 62), (65, 65),
    (72, 49), (75, 52),
    (82, 34), (85, 37),
    (91, 18), (95, 7),                            # final surge to the top right
]
P = [(x / 100.0 * W, y / 100.0 * H) for x, y in PTS_PCT]


def catmull_rom_to_bezier(pts, t):
    """Catmull-Rom through `pts` expressed as cubic Beziers."""
    d = ["M %.1f %.1f" % pts[0]]
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        c1 = (p1[0] + (p2[0] - p0[0]) * t / 3.0, p1[1] + (p2[1] - p0[1]) * t / 3.0)
        c2 = (p2[0] - (p3[0] - p1[0]) * t / 3.0, p2[1] - (p3[1] - p1[1]) * t / 3.0)
        d.append("C %.1f %.1f %.1f %.1f %.1f %.1f" % (c1 + c2 + p2))
    return " ".join(d)


def bezier_pt(p0, c1, c2, p1, s):
    u = 1 - s
    return (u**3 * p0[0] + 3 * u * u * s * c1[0] + 3 * u * s * s * c2[0] + s**3 * p1[0],
            u**3 * p0[1] + 3 * u * u * s * c1[1] + 3 * u * s * s * c2[1] + s**3 * p1[1])


def arc_length(pts, t, steps=400):
    """Numeric arc length -- Safari's pathLength is unreliable, so the dash
    length gets hardcoded into the CSS instead."""
    total = 0.0
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        c1 = (p1[0] + (p2[0] - p0[0]) * t / 3.0, p1[1] + (p2[1] - p0[1]) * t / 3.0)
        c2 = (p2[0] - (p3[0] - p1[0]) * t / 3.0, p2[1] - (p3[1] - p1[1]) * t / 3.0)
        prev = p1
        for k in range(1, steps + 1):
            cur = bezier_pt(p1, c1, c2, p2, k / float(steps))
            total += math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            prev = cur
    return total


d = catmull_rom_to_bezier(P, TENSION)
length = arc_length(P, TENSION)
dash = int(math.ceil(length)) + 20          # pad so the tail fully clears

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hero_line.txt"), "w") as fh:
    fh.write("d=%s\n\ndash=%d\n" % (d, dash))
print("d=%s\n" % d)
print("dash=%d" % dash)
