# Manic AI - public podcast feed

This is the **public** home for the Manic AI podcast feed and audio. It exists so podcast apps
and directories (Apple Podcasts, Spotify) can fetch the feed and episodes anonymously. The source
briefings are generated privately in `colinmoroney/manic-mondai-project`; only the finished audio +
feed live here.

**Feed URL (submit this to directories / subscribe by URL):**
```
https://colinmoroney.github.io/manic-mondai-podcast/feed.xml
```

## Adding an episode

After NotebookLM generates the audio overview and you download the `.m4a`, it's a one-liner - the
**episode title and show notes auto-fill from that week's digest**:

```bash
python3 add_episode.py --file ~/Downloads/Some_NotebookLM_Title.m4a --date 2026-06-25
git add -A && git commit -m "episode 2026-06-25" && git push
```

What it does automatically:
- **Title** - from the NotebookLM filename (it auto-titles descriptively), with the date appended.
  Falls back to the digest's top story headline if the filename isn't descriptive.
- **Show notes / description** - built from the matching digest's *Threads this week* plus a plain
  list of the week's story headlines (`../manic-mondai-project/digests/<date>-digest.md`).
- Copies the audio to `episodes/<date>.m4a`, computes size + duration, prepends a new `<item>` to `feed.xml`.

Override anything: `--title`, `--summary`, `--season`, `--episode`, `--digest` (season defaults to 1; episode auto-increments).
Preview without writing: add `--dry-run`.

GitHub Pages serves the update within a minute or two; subscribed apps pick it up on their next refresh.
(Requires the private `manic-mondai-project` repo checked out as a sibling folder for the auto-notes.)

## Files
- `feed.xml` - the RSS feed (newest episode first)
- `episodes/` - the published `.m4a` files
- `cover.jpg` - show artwork (3000×3000)
- `add_episode.py` - feed updater

## Getting it searchable (one-time)
1. **Apple Podcasts:** sign in at [Podcasts Connect](https://podcastsconnect.apple.com), add the feed URL, validate, submit.
2. **Spotify:** add the feed URL at [Spotify for Creators](https://creators.spotify.com).
3. Validate first at [castfeedvalidator.com](https://castfeedvalidator.com) or [podba.se/validate](https://podba.se/validate/).

Until submitted, the show is private - listeners can still add it by pasting the feed URL into any app.

## Notes
- GitHub Pages is fine for a personal, low-traffic feed. If it ever grows, move audio to a dedicated
  podcast host and only the enclosure URLs change.
- Episode dates match the source digest date in `manic-mondai-project/digests/`.
