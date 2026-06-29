#!/usr/bin/env python3
"""Add a NotebookLM episode (.m4a) to the Manic AI public feed.

Common use (one-liner - title + show notes auto-filled from that week's digest):
  python3 add_episode.py --file ~/Downloads/Some_NotebookLM_Title.m4a --date 2026-06-25
  git add -A && git commit -m "episode 2026-06-25" && git push

Options:
  --file     path to the NotebookLM .m4a            (required)
  --date     YYYY-MM-DD, matches the digest date    (required)
  --digest   source digest .md  (default: ../manic-mondai-project/digests/<date>-digest.md)
  --title    override the episode title
  --summary  override the description (plain text)
  --season   season number (default: 1)
  --episode  episode number (default: auto = current episode count + 1)
  --dry-run  print what would be written; change nothing
  --feed     feed file (default: feed.xml)

Title priority:  --title > a descriptive NotebookLM filename > first story headline from the digest > "Manic AI - <date>".
Description:     --summary, else built from the digest's "Threads this week" plus a plain list of the week's stories.
Stdlib only; uses macOS `afinfo` for duration. No em-dashes (Colin's preference).
"""
import argparse, html, os, re, shutil, subprocess
from datetime import datetime, timezone
from email.utils import format_datetime

BASE_URL = "https://colinmoroney.github.io/manic-mondai-podcast"
MARKER = "<!-- EPISODES_BELOW:"


def duration_hms(path):
    if path and os.path.exists(path):
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
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=noprint_wrappers=1:nokey=1", path],
                                   capture_output=True, text=True)
                s = int(float(r.stdout.strip()))
                return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
            except Exception:
                pass
    return "00:00:00"


def md_strip(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return s.strip()


def parse_digest(path):
    """Return (threads: list[str], stories: list[str]) - headlines only, no links."""
    text = open(path, encoding="utf-8").read()
    threads = []
    m = re.search(r"##\s*Threads this week\s*(.+?)(?:\n##\s|\Z)", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                threads.append(md_strip(line[2:]))
    stories = []
    for b in re.split(r"\n###\s+", text)[1:]:
        headline = re.sub(r"^\d+\.\s*", "", b.splitlines()[0]).strip()
        if headline:
            stories.append(headline)
    return threads, stories


def build_meta(args):
    threads, stories = ([], [])
    if args.digest and os.path.exists(args.digest):
        threads, stories = parse_digest(args.digest)

    title = args.title
    if not title:
        cleaned = re.sub(r"[_]+", " ", os.path.splitext(os.path.basename(args.file))[0]).strip()
        datey = re.fullmatch(r"[\d\-.\s]+", cleaned) is not None
        if cleaned and not datey and len(cleaned.split()) >= 3:
            title = cleaned
        elif stories:
            title = stories[0]
        else:
            title = "Manic AI"

    if args.summary:
        summary_plain = args.summary
    elif threads:
        summary_plain = " ".join(threads)
    elif stories:
        summary_plain = "In this episode: " + "; ".join(stories[:4]) + "."
    else:
        summary_plain = "The latest AI news, twice a week."

    parts = [f"<p>{html.escape(t)}</p>" for t in threads]
    if stories:
        parts.append("<p><strong>In this episode</strong></p><ul>")
        for h in stories:
            parts.append(f"<li>{html.escape(h)}</li>")
        parts.append("</ul>")
    notes_html = "\n".join(parts) if parts else f"<p>{html.escape(summary_plain)}</p>"

    nodash = lambda s: s.replace("—", "-").replace("–", "-")  # Colin dislikes em/en dashes
    return nodash(title), nodash(summary_plain), nodash(notes_html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--digest")
    ap.add_argument("--title")
    ap.add_argument("--summary")
    ap.add_argument("--season", default="1")
    ap.add_argument("--episode")
    ap.add_argument("--feed", default="feed.xml")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.digest:
        a.digest = f"../manic-mondai-project/digests/{a.date}-digest.md"

    with open(a.feed, encoding="utf-8") as f:
        feed = f.read()
    episode = a.episode or str(feed.count("</item>") + 1)  # count closing tags; marker comment contains "<item>"

    title, summary_plain, notes_html = build_meta(a)
    dur = duration_hms(a.file)

    if a.dry_run:
        print("DRY RUN - nothing written\n")
        print("digest :", a.digest, "(found)" if os.path.exists(a.digest) else "(NOT FOUND - title/notes will be thin)")
        print("title  :", title)
        print(f"season : {a.season}   episode: {episode}")
        print("duration:", dur)
        print("\n--- itunes:summary (plain) ---\n" + summary_plain[:700])
        print("\n--- description / show notes (html) ---\n" + notes_html[:1500])
        return

    if MARKER not in feed:
        raise SystemExit(f"marker '{MARKER}' not found in {a.feed}")
    os.makedirs("episodes", exist_ok=True)
    dest = os.path.join("episodes", f"{a.date}.m4a")
    if os.path.abspath(a.file) != os.path.abspath(dest):
        shutil.copyfile(a.file, dest)
    size = os.path.getsize(dest)
    dt = datetime.strptime(a.date, "%Y-%m-%d").replace(hour=18, tzinfo=timezone.utc)
    esc = lambda s: html.escape(s, quote=False)

    item = f"""    <item>
      <title>{esc(title)}</title>
      <itunes:title>{esc(title)}</itunes:title>
      <itunes:season>{esc(a.season)}</itunes:season>
      <itunes:episode>{esc(episode)}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <description><![CDATA[{notes_html}]]></description>
      <content:encoded><![CDATA[{notes_html}]]></content:encoded>
      <itunes:summary>{esc(summary_plain)}</itunes:summary>
      <pubDate>{format_datetime(dt)}</pubDate>
      <enclosure url="{BASE_URL}/episodes/{a.date}.m4a" length="{size}" type="audio/x-m4a"/>
      <guid isPermaLink="false">manic-mondai-{a.date}</guid>
      <itunes:duration>{dur}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>
"""
    i = feed.index("\n", feed.index(MARKER)) + 1
    with open(a.feed, "w", encoding="utf-8") as f:
        f.write(feed[:i] + item + feed[i:])
    print(f"Added S{a.season}E{episode}: '{title}' ({size} bytes, {dur}).")
    print(f'Next: git add -A && git commit -m "episode {a.date}" && git push')


if __name__ == "__main__":
    main()
