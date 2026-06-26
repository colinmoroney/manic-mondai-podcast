#!/usr/bin/env python3
"""Add a NotebookLM episode (.m4a) to the Manic Mond-AI public feed.

Usage:
  python3 add_episode.py --file ~/Downloads/Some_NotebookLM_Title.m4a --date 2026-06-25 \
      --title "Episode title" --summary "One-line summary of the week."

What it does:
  1. Copies the audio to episodes/<date>.m4a
  2. Computes byte length + duration (macOS `afinfo`, falls back to ffprobe)
  3. Prepends a new <item> to feed.xml

Then publish with:
  git add -A && git commit -m "episode <date>" && git push

Stdlib only. Run it from the root of the manic-mondai-podcast repo.
"""
import argparse, os, re, shutil, subprocess
from datetime import datetime, timezone
from email.utils import format_datetime

BASE_URL = "https://colinmoroney.github.io/manic-mondai-podcast"
MARKER = "<!-- EPISODES_BELOW:"


def duration_hms(path):
    try:
        out = subprocess.run(["afinfo", path], capture_output=True, text=True).stdout
        m = re.search(r"estimated duration:\s*([\d.]+)\s*sec", out)
        if m:
            s = int(float(m.group(1)))
            return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    except Exception:
        pass
    if shutil.which("ffprobe"):
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                capture_output=True, text=True)
            s = int(float(r.stdout.strip()))
            return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
        except Exception:
            pass
    return "00:00:00"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="path to the NotebookLM .m4a")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (matches the digest date)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--feed", default="feed.xml")
    a = ap.parse_args()

    os.makedirs("episodes", exist_ok=True)
    dest = os.path.join("episodes", f"{a.date}.m4a")
    if os.path.abspath(a.file) != os.path.abspath(dest):
        shutil.copyfile(a.file, dest)

    size = os.path.getsize(dest)
    dur = duration_hms(dest)
    dt = datetime.strptime(a.date, "%Y-%m-%d").replace(hour=18, tzinfo=timezone.utc)
    item = f"""    <item>
      <title>{esc(a.title)}</title>
      <description>{esc(a.summary)}</description>
      <itunes:summary>{esc(a.summary)}</itunes:summary>
      <pubDate>{format_datetime(dt)}</pubDate>
      <enclosure url="{BASE_URL}/episodes/{a.date}.m4a" length="{size}" type="audio/x-m4a"/>
      <guid isPermaLink="false">manic-mondai-{a.date}</guid>
      <itunes:duration>{dur}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>
"""
    with open(a.feed, encoding="utf-8") as f:
        feed = f.read()
    if MARKER not in feed:
        raise SystemExit(f"marker '{MARKER}' not found in {a.feed}")
    i = feed.index("\n", feed.index(MARKER)) + 1
    feed = feed[:i] + item + feed[i:]
    with open(a.feed, "w", encoding="utf-8") as f:
        f.write(feed)

    print(f"Added {dest} ({size} bytes, {dur}).")
    print(f'Next: git add -A && git commit -m "episode {a.date}" && git push')


if __name__ == "__main__":
    main()
