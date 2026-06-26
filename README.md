# Manic Mond-AI — public podcast feed

This is the **public** home for the Manic Mond-AI podcast feed and audio. It exists so podcast apps
and directories (Apple Podcasts, Spotify) can fetch the feed and episodes anonymously. The source
briefings are generated privately in `colinmoroney/manic-mondai-project`; only the finished audio +
feed live here.

**Feed URL (submit this to directories / subscribe by URL):**
```
https://colinmoroney.github.io/manic-mondai-podcast/feed.xml
```

## Adding an episode

After NotebookLM generates the audio overview and you download the `.m4a`:

```bash
python3 add_episode.py \
  --file ~/Downloads/Some_NotebookLM_Title.m4a \
  --date 2026-06-25 \
  --title "Episode title" \
  --summary "One-line summary of the week."

git add -A && git commit -m "episode 2026-06-25" && git push
```

`add_episode.py` copies the file to `episodes/<date>.m4a`, computes its size and duration, and prepends
a new `<item>` to `feed.xml`. GitHub Pages serves the update within a minute or two; subscribed apps pick
it up on their next refresh.

## Files
- `feed.xml` — the RSS feed (newest episode first)
- `episodes/` — the published `.m4a` files
- `cover.jpg` — show artwork (3000×3000)
- `add_episode.py` — feed updater

## Getting it searchable (one-time)
1. **Apple Podcasts:** sign in at [Podcasts Connect](https://podcastsconnect.apple.com), add the feed URL, validate, submit.
2. **Spotify:** add the feed URL at [Spotify for Creators](https://creators.spotify.com).
3. Validate first at [castfeedvalidator.com](https://castfeedvalidator.com) or [podba.se/validate](https://podba.se/validate/).

Until submitted, the show is private — listeners can still add it by pasting the feed URL into any app.

## Notes
- GitHub Pages is fine for a personal, low-traffic feed. If it ever grows, move audio to a dedicated
  podcast host and only the enclosure URLs change.
- Episode dates match the source digest date in `manic-mondai-project/digests/`.
