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
python3 add_episode.py --file ~/Downloads/Some_NotebookLM_Title.m4a --date 2026-07-06
git add feed.xml && git commit -m "episode 2026-07-06" && git push
```

What it does automatically:
- **Uploads the audio to the GitHub Release** tagged `episodes` as `<date>.m4a` (public, CDN-served),
  and points the feed enclosure there. Audio is NOT committed to the repo, so Pages builds stay tiny.
- **Title** - from the NotebookLM filename (it auto-titles descriptively).
  Falls back to the digest's top story headline if the filename isn't descriptive.
- **Show notes / description** - built from the matching digest's *Threads this week* plus a plain
  list of the week's story headlines (`../manic-mondai-project/digests/<date>-digest.md`).
- Computes size + duration and prepends a new `<item>` to `feed.xml`.

Override anything: `--title`, `--summary`, `--season`, `--episode`, `--digest`, `--force` (season defaults to 1; episode auto-increments).
Preview without writing/uploading: add `--dry-run`.

Requires the `gh` CLI (authenticated) for the upload, and the private `manic-mondai-project` repo
checked out as a sibling folder for the auto-notes.

## Files
- `feed.xml` - the RSS feed (newest episode first); Pages serves this
- `cover.jpg` - show artwork (3000×3000); Pages serves this
- `add_episode.py` - feed updater (uploads audio to the Release, updates the feed)
- **Audio** lives in the GitHub Release [`episodes`](https://github.com/colinmoroney/manic-mondai-podcast/releases/tag/episodes), not in the repo

## Getting it searchable (one-time)
1. **Apple Podcasts:** sign in at [Podcasts Connect](https://podcastsconnect.apple.com), add the feed URL, validate, submit.
2. **Spotify:** add the feed URL at [Spotify for Creators](https://creators.spotify.com).
3. Validate first at [castfeedvalidator.com](https://castfeedvalidator.com) or [podba.se/validate](https://podba.se/validate/).

Until submitted, the show is private - listeners can still add it by pasting the feed URL into any app.

## Notes
- Audio is hosted as GitHub Release assets (CDN-served), so GitHub Pages only ever builds the small
  `feed.xml` + `cover.jpg` - fast, and no repo-size problem as episodes accumulate.
- Episode dates match the source digest date in `manic-mondai-project/digests/`.
