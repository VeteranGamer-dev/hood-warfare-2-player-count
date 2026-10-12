#!/usr/bin/env python3
"""Record Hood Warfare 2's concurrent Steam players and redraw the chart.

Runs hourly in GitHub Actions: appends one row to data/players.csv, redraws
chart.png and refreshes the stats block in README.md.

    python scripts/record.py            fetch, append, redraw
    python scripts/record.py --render   redraw from the existing CSV only

Standard library + Pillow only.
"""
import csv
import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

APP_ID = 5155360
API = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={APP_ID}"
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "players.csv"
CHART_PATH = ROOT / "chart.png"
README_PATH = ROOT / "README.md"
FONTS = ROOT / "fonts"

WINDOW = dt.timedelta(days=30)        # chart shows the last 30 days
MAX_GAP = dt.timedelta(hours=3)       # readings further apart than this are not joined

# Colours from the hoodwarfare2.org "night street" theme.
BG = (18, 15, 12)            # page canvas
GRID = (43, 39, 35)          # hairline, one step off the canvas
INK = (235, 231, 226)        # primary text
MUTED = (175, 170, 163)      # secondary text
LINE = (250, 187, 65)        # sodium-streetlight amber
AREA = (250, 187, 65, 26)    # same hue, ~10% wash


# ---------------------------------------------------------------- data

def fetch_players():
    for attempt in range(3):
        try:
            req = urllib.request.Request(API, headers={"User-Agent": "hw2-player-count-tracker"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)["response"]
            if data.get("result") == 1:
                return int(data["player_count"])
            print(f"unexpected response: {data}", file=sys.stderr)
        except Exception as e:  # network hiccups are normal; retry
            print(f"fetch attempt {attempt + 1} failed: {e}", file=sys.stderr)
        time.sleep(10)
    return None


def read_rows():
    rows = []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = dt.datetime.strptime(r["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
            rows.append((t, int(r["players"]), r["source"]))
    return sorted(rows)


def append_row(t, players):
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="
").writerow([t.strftime("%Y-%m-%dT%H:%M:%SZ"), players, "steam_api"])


# ---------------------------------------------------------------- time

def us_eastern(t):
    """UTC datetime -> (US Eastern wall time, 'EDT'/'EST'). No tzdata needed."""
    def nth_sunday(month, n):
        first = dt.datetime(t.year, month, 1, tzinfo=dt.timezone.utc)
        return first + dt.timedelta(days=(6 - first.weekday()) % 7, weeks=n - 1)
    dst_start = nth_sunday(3, 2) + dt.timedelta(hours=7)   # 2 AM EST
    dst_end = nth_sunday(11, 1) + dt.timedelta(hours=6)    # 2 AM EDT
    offset = -4 if dst_start <= t < dst_end else -5
    return t + dt.timedelta(hours=offset), ("EDT" if offset == -4 else "EST")


def fmt_et(t, with_year=False):
    local, zone = us_eastern(t)
    hour = local.strftime("%I").lstrip("0")
    day = f"{local:%b} {local.day}" + (f", {local.year}" if with_year else "")
    return f"{day}, {hour}:{local:%M} {local:%p} {zone}"


# ---------------------------------------------------------------- chart

S = 3                      # supersample factor; drawn at 3x, saved at 2x
W, H = 800, 400            # logical size (CSS pixels at 1x)
PLOT = (60, 92, W - 32, H - 58)   # left, top, right, bottom


def font(name, size, axes):
    f = ImageFont.truetype(str(FONTS / name), int(size * S))
    f.set_variation_by_axes(axes)
    return f


def compact(v):
    if v >= 1000:
        s = f"{v / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{s}K"
    return str(v)


def nice_step(top):
    for step in (50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000, 100000):
        if top / step <= 5:
            return step
    return 200000


def render(rows):
    now = rows[-1][0]
    rows = [r for r in rows if r[0] >= now - WINDOW]
    t0, t1 = rows[0][0], rows[-1][0]
    if t1 - t0 < dt.timedelta(hours=24):
        t0 = t1 - dt.timedelta(hours=24)
    peak = max(rows, key=lambda r: (r[1], r[0]))
    step = nice_step(peak[1] * 1.12)
    ymax = -(-int(peak[1] * 1.12) // step) * step

    L, T, R, B = PLOT
    span = (t1 - t0).total_seconds()
    X = lambda t: (L + (t - t0).total_seconds() / span * (R - L)) * S
    Y = lambda v: (B - v / ymax * (B - T)) * S

    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    d = ImageDraw.Draw(img)
    title = font("BigShoulders.ttf", 27, [800, 10])
    body = font("Inter.ttf", 12.5, [14, 450])
    small = font("Inter.ttf", 11, [14, 450])
    label_b = font("Inter.ttf", 13, [14, 650])

    d.text((24 * S, 18 * S), "HOOD WARFARE 2 · PLAYERS ONLINE ON STEAM", font=title, fill=INK)
    d.text((24 * S, 54 * S), f"Concurrent players, recorded hourly · updated {fmt_et(t1)}",
           font=body, fill=MUTED)

    # y grid + labels
    for v in range(0, ymax + 1, step):
        y = Y(v)
        d.line([(L * S, y), (R * S, y)], fill=GRID, width=S)
        tw = d.textlength(compact(v), font=small)
        d.text((L * S - 10 * S - tw, y - 7 * S), compact(v), font=small, fill=MUTED)

    # x ticks: pick an interval that gives 3-8 labels, aligned to US Eastern wall time
    for hours in (3, 6, 12, 24, 48, 168):
        if 3 <= span / 3600 / hours <= 8:
            break
    local0, _ = us_eastern(t0)
    tick_local = local0.replace(minute=0, second=0, microsecond=0)
    tick_local -= dt.timedelta(hours=tick_local.hour % min(hours, 24))
    offset = local0 - t0
    while tick_local - offset <= t1:
        t = tick_local - offset
        if t >= t0:
            x = X(t)
            d.line([(x, B * S), (x, B * S + 5 * S)], fill=GRID, width=S)
            lab = f"{tick_local:%b} {tick_local.day}" if tick_local.hour == 0 else \
                tick_local.strftime("%I %p").lstrip("0")
            tw = d.textlength(lab, font=small)
            d.text((x - tw / 2, B * S + 9 * S), lab, font=small, fill=MUTED)
        tick_local += dt.timedelta(hours=hours)

    # series: runs of hourly readings no more than MAX_GAP apart; manual readings stand alone
    runs, cur = [], [rows[0]]
    for prev, r in zip(rows, rows[1:]):
        if r[0] - prev[0] <= MAX_GAP and r[2] == prev[2] == "steam_api":
            cur.append(r)
        else:
            runs.append(cur)
            cur = [r]
    runs.append(cur)

    wash = Image.new("RGBA", img.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(wash)
    for run in runs:
        if len(run) > 1:
            pts = [(X(t), Y(v)) for t, v, _ in run]
            wd.polygon(pts + [(pts[-1][0], Y(0)), (pts[0][0], Y(0))], fill=AREA)
    img = Image.alpha_composite(img, wash)
    d = ImageDraw.Draw(img)
    for run in runs:
        pts = [(X(t), Y(v)) for t, v, _ in run]
        if len(pts) > 1:
            d.line(pts, fill=LINE, width=2 * S, joint="curve")
        for x, y in pts if len(pts) == 1 else []:
            d.ellipse([x - 3 * S, y - 3 * S, x + 3 * S, y + 3 * S], fill=LINE)

    def marker(t, v):
        x, y = X(t), Y(v)
        r, ring = 4 * S, 2 * S
        d.ellipse([x - r - ring, y - r - ring, x + r + ring, y + r + ring], fill=BG)
        d.ellipse([x - r, y - r, x + r, y + r], fill=LINE)
        return x, y

    def callout(x, y, head, sub, prefer="left"):
        hw = max(d.textlength(head, font=label_b), d.textlength(sub, font=small))
        pad = 10 * S
        tx = x - hw - pad if prefer == "left" else x + pad
        tx = min(max(tx, L * S), R * S - hw)
        ty = max(y - 34 * S, T * S - 6 * S)
        d.text((tx, ty), head, font=label_b, fill=INK)
        d.text((tx, ty + 16 * S), sub, font=small, fill=MUTED)

    latest = rows[-1]
    lx, ly = marker(latest[0], latest[1])
    if peak[0] == latest[0]:
        callout(lx, ly, f"Now {latest[1]:,} · peak so far", fmt_et(latest[0]), "left")
    else:
        px, py = marker(peak[0], peak[1])
        callout(px, py, f"Peak {peak[1]:,}", fmt_et(peak[0]), "right" if px < (L + R) / 2 * S else "left")
        if abs(lx - px) > 150 * S:
            callout(lx, ly, f"Now {latest[1]:,}", fmt_et(latest[0]), "left")

    d.text((24 * S, (H - 24) * S),
           "Source: Steam Web API · github.com/VeteranGamer-dev/hood-warfare-2-player-count · hoodwarfare2.org",
           font=small, fill=MUTED)

    img.convert("RGB").resize((W * 2, H * 2), Image.LANCZOS).save(CHART_PATH, optimize=True)


# ---------------------------------------------------------------- README

def update_readme(rows):
    latest = rows[-1]
    peak = max(rows, key=lambda r: (r[1], r[0]))
    day_ago = latest[0] - dt.timedelta(hours=24)
    last24 = [r for r in rows if r[0] >= day_ago]
    peak24 = max(last24, key=lambda r: (r[1], r[0]))
    first = rows[0][0]
    block = "\n".join([
        "<!-- stats:start -->",
        "| | Players | When (US Eastern) |",
        "|---|---:|---|",
        f"| Latest reading | **{latest[1]:,}** | {fmt_et(latest[0], True)} |",
        f"| Peak in the last 24 hours | {peak24[1]:,} | {fmt_et(peak24[0], True)} |",
        f"| Highest reading recorded | {peak[1]:,} | {fmt_et(peak[0], True)} |",
        "",
        f"{len(rows):,} readings since {fmt_et(first, True)}.",
        "<!-- stats:end -->",
    ])
    text = README_PATH.read_text(encoding="utf-8")
    a, b = text.index("<!-- stats:start -->"), text.index("<!-- stats:end -->") + len("<!-- stats:end -->")
    README_PATH.write_text(text[:a] + block + text[b:], encoding="utf-8")


def main():
    if "--render" not in sys.argv:
        players = fetch_players()
        if players is None:
            print("no reading this hour; leaving files unchanged")
            return
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        append_row(now, players)
        print(f"{now:%Y-%m-%dT%H:%M:%SZ} {players}")
    rows = read_rows()
    render(rows)
    update_readme(rows)


if __name__ == "__main__":
    main()
