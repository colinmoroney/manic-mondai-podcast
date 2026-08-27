#!/usr/bin/env python3
"""Add a NotebookLM episode to the Manic AI public feed.

Audio is uploaded to the archive.org item "manic-ai-podcast" (public, streams with a real
audio/* content-type + byte-range support) and the feed's enclosure points there. Only
feed.xml + cover live in the repo, so GitHub Pages builds stay tiny.

Why archive.org, not GitHub Releases: GitHub forces Content-Disposition: attachment and
Content-Type: application/octet-stream on every release-asset download, so Apple Podcasts
refuses to stream them ("This episode can't be played on this device"). archive.org serves
audio inline with the right headers.

Common use (one-liner - title + show notes auto-filled from that week's digest):
  python3 add_episode.py --file ~/Downloads/Some_NotebookLM_Title.m4a --date 2026-07-06
  git add feed.xml && git commit -m "episode 2026-07-06" && git push

Options:
  --file     path to the NotebookLM .m4a            (required)
  --date     YYYY-MM-DD, matches the digest date    (required)
  --digest   source digest .md  (default: ../manic-mondai-project/digests/<date>-digest.md).
             A missing digest is a hard error, never a fallback: the routine commits digests
             to origin, so a clone that is behind silently has no digest for today, and
             guessing would attach the PREVIOUS episode's show notes to this one. Pass
             --digest explicitly to use a file the date does not name.
  --no-fetch skip the git-freshness check on the digest repo (no network)
  --title    override the episode title
  --summary  override the description (plain text)
  --season   season number (default: 1)
  --episode  episode number (default: auto = current episode count + 1)
  --force    allow re-using a date already in the feed (also re-uploads/clobbers the archive.org
             file). It only lifts the duplicate-date guard, it does NOT replace the existing
             item: the new one is appended alongside it and auto-numbered one higher, so the
             feed ends up with two items for the same date. To REGENERATE an entry (a digest
             fixed after publishing, say), discard the unpushed feed edit and re-run plain:
               git checkout feed.xml
               python3 add_episode.py --file <mixed.m4a> --date <date>
             That renumbers correctly and re-uploads the same audio over the old asset. If the
             bad entry is already pushed, delete its <item> block by hand before re-running.
  --dry-run  print what would be written; upload/change nothing
  --feed     feed file (default: feed.xml)

Requires the `ia` CLI (internetarchive, authenticated via ~/.config/internetarchive/ia.ini)
to upload the audio. No em-dashes (Colin's preference).
"""
import argparse, html, os, re, shutil, subprocess
from datetime import datetime, timezone
from email.utils import format_datetime

REPO = "colinmoroney/manic-mondai-podcast"
IA_ITEM = "manic-ai-podcast-audio"
RELEASE_URL = f"https://archive.org/download/{IA_ITEM}"
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


def repo_behind(path):
    """How many commits the repo holding `path` is behind its upstream.

    Returns (behind, repo_dir). behind is None when the question does not apply or
    cannot be answered - no git, not a repo, no upstream, network down. None means
    "unknown", never "up to date", so callers must not treat it as a green light.
    Fetches first, because the digest is committed by the routine on another machine.
    """
    d = os.path.dirname(os.path.abspath(path)) or "."
    if not shutil.which("git") or not os.path.isdir(d):
        return None, d

    def git(*args, timeout=20):
        try:
            r = subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    if git("rev-parse", "--is-inside-work-tree") != "true":
        return None, d
    root = git("rev-parse", "--show-toplevel") or d
    git("fetch", "--quiet", timeout=90)  # best effort; offline just leaves the refs stale
    upstream = git("rev-parse", "--abbrev-ref", "@{upstream}")
    if not upstream:
        return None, root
    n = git("rev-list", "--count", f"HEAD..{upstream}")
    return (int(n) if n and n.isdigit() else None), root


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
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip the git-freshness check on the digest repo (no network)")
    ap.add_argument("--force", action="store_true",
                    help="allow a date already present in the feed. Appends a SECOND item, it does "
                         "not replace the existing one. To regenerate an entry instead: "
                         "git checkout feed.xml, then re-run without --force")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    explicit_digest = bool(a.digest)
    if not a.digest:
        a.digest = f"../manic-mondai-project/digests/{a.date}-digest.md"

    # The digest lives in the private repo and is written there by the cloud routine,
    # so "the file is not on disk" usually means "this clone has not pulled yet".
    behind, repo_dir = (None, os.path.dirname(os.path.abspath(a.digest)))
    if not a.no_fetch:
        behind, repo_dir = repo_behind(a.digest)

    if not os.path.exists(a.digest):
        why = f"ERROR: no digest for {a.date} at {a.digest}\n\n"
        if explicit_digest:
            why += "That path was given with --digest and does not exist."
        else:
            why += ("Refusing to fall back to another date. The show notes are built from the\n"
                    "digest, so guessing here publishes the PREVIOUS episode's notes over this\n"
                    "episode's audio, which is worse than not publishing at all.\n\n")
            if behind:
                why += (f"This clone is {behind} commit(s) behind its remote, which is almost\n"
                        f"certainly the cause. Pull, then re-run:\n"
                        f"  git -C {repo_dir} pull\n\n")
            elif behind is None:
                why += ("Could not check whether this clone is behind its remote (no git, no\n"
                        "upstream, or no network). If the routine has already written this\n"
                        "digest, pulling the private repo is the usual fix.\n\n")
            why += "To use a file this date does not name, pass it explicitly:\n  --digest path/to/digest.md"
        raise SystemExit(why)

    if behind:
        print(f"WARNING: the digest repo is {behind} commit(s) behind its remote.\n"
              f"         Using the local {os.path.basename(a.digest)}, which may be stale.\n"
              f"         git -C {repo_dir} pull")

    with open(a.feed, encoding="utf-8") as f:
        feed = f.read()
    if f"manic-mondai-{a.date}" in feed and not a.force:
        raise SystemExit(f"ERROR: an episode dated {a.date} is already in the feed - did you forget to "
                         f"update --date? Re-run with --force to add it anyway.")
    episode = a.episode or str(feed.count("</item>") + 1)

    title, summary_plain, notes_html = build_meta(a)
    dur = duration_hms(a.file)
    size = os.path.getsize(a.file)

    if a.dry_run:
        print("DRY RUN - nothing uploaded or written\n")
        print("digest :", a.digest, "(found)" if os.path.exists(a.digest) else "(NOT FOUND)")
        print("title  :", title)
        print(f"season : {a.season}   episode: {episode}")
        print("audio  :", f"{RELEASE_URL}/{a.date}.m4a", f"({size} bytes, {dur})")
        print("\n--- itunes:summary ---\n" + summary_plain[:700])
        print("\n--- show notes (html) ---\n" + notes_html[:1500])
        return

    if MARKER not in feed:
        raise SystemExit(f"marker '{MARKER}' not found in {a.feed}")

    # Upload the audio to the archive.org item as <date>.m4a (stage a copy so the asset name is clean).
    ia_bin = shutil.which("ia") or os.path.expanduser("~/Library/Python/3.14/bin/ia")
    if not os.path.exists(ia_bin):
        raise SystemExit("`ia` CLI not found. Install with: python3 -m pip install --user "
                         "--break-system-packages internetarchive")
    stage = os.path.join("/tmp", f"{a.date}.m4a")
    shutil.copyfile(a.file, stage)
    print(f"Uploading audio to archive.org item '{IA_ITEM}' as {a.date}.m4a ({size} bytes)...")
    r = subprocess.run([ia_bin, "upload", IA_ITEM, stage, "--metadata=mediatype:audio",
                        "--no-derive", "--retries=5"],
                       capture_output=True, text=True)
    os.remove(stage)
    if r.returncode != 0:
        raise SystemExit(f"ia upload failed:\n{r.stderr.strip()}")

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
      <enclosure url="{RELEASE_URL}/{a.date}.m4a" length="{size}" type="audio/x-m4a"/>
      <guid isPermaLink="false">manic-mondai-{a.date}</guid>
      <itunes:duration>{dur}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>
"""
    i = feed.index("\n", feed.index(MARKER)) + 1
    with open(a.feed, "w", encoding="utf-8") as f:
        f.write(feed[:i] + item + feed[i:])
    print(f"Added S{a.season}E{episode}: '{title}' ({size} bytes, {dur}).")
    print(f'Next: git add {a.feed} && git commit -m "episode {a.date}" && git push')


if __name__ == "__main__":
    main()
