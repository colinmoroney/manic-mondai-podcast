# Manic AI - public podcast feed and website

This is the **public** home of the Manic AI podcast: the RSS feed, the show artwork and the
[thisismanic.ai](https://thisismanic.ai) landing page. Podcast apps and directories fetch the feed
from here anonymously. The briefings, transcripts and audio rendering live in the private
`colinmoroney/manic-mondai-project` repo; only the finished feed and site are published here.

**Feed URL (subscribe by URL, or submit to directories):**
```
https://thisismanic.ai/feed.xml
```

Listen on [Apple Podcasts](https://podcasts.apple.com/ca/podcast/manic-ai/id6784824356) or
[Spotify](https://open.spotify.com/show/033FhHakKuEYXWZg6WkTGW). New episodes every Monday and Thursday.

## How an episode gets made

1. A scheduled routine in the private repo writes `digests/<date>-digest.md` every Monday and Thursday.
2. Claude turns the digest into a two-host transcript plus episode notes
   (`podcast/transcripts/<date>-transcript.txt` and `<date>-episode-notes.md`).
3. `podcast/make_episode.py` voices it with the ElevenLabs Text to Dialogue API and adds the intro/outro
   music, giving `podcast/episodes/<date>.m4a`.
4. `add_episode.py` in this repo publishes it (below).

## Publishing an episode

Pull the private repo first, so today's digest and notes are on disk. Then, from this repo:

```bash
python3 add_episode.py --file ../manic-mondai-project/podcast/episodes/<date>.m4a --date <date> --dry-run
python3 add_episode.py --file ../manic-mondai-project/podcast/episodes/<date>.m4a --date <date>
git add feed.xml && git commit -m "episode <date>" && git push
```

Check the dry run before the real one: the `digest` line should name the date you expect, and the
`title` line should say `(from episode notes)`.

What it does:
- **Uploads the audio to archive.org** (item `manic-ai-podcast-audio`) as `<date>.m4a` and points the
  feed enclosure there. Audio is never committed to this repo.
- **Title** comes from the `**Title:**` line in the episode notes
  (`../manic-mondai-project/podcast/transcripts/<date>-episode-notes.md`).
- **Show notes** are built from the digest's *Threads this week* plus a list of that episode's story
  headlines (`../manic-mondai-project/digests/<date>-digest.md`).
- Works out size and duration, numbers the episode, and adds a new `<item>` at the top of `feed.xml`.
- **Refuses to guess.** A missing digest is a hard error, and it fetches the private repo first to warn
  if your clone is behind, so an episode never goes out with the previous episode's notes.

Overrides: `--title`, `--summary`, `--notes`, `--digest`, `--season`, `--episode`, `--force`,
`--no-fetch`. Run `python3 add_episode.py --help` or read the docstring for details.

Requires the `ia` CLI (`pip install internetarchive`, then `ia configure`) and the private
`manic-mondai-project` repo checked out as a sibling folder.

## Sample issue and auto-reply

- `sample/` - the Manic AI for RevOps sample issue: `index.html` (web version with the audio player), the
  two-page PDF and the 12-minute `revops-sample-2026-10-12.m4a`. These are served from thisismanic.ai/sample/.
  The m4a is deliberately un-ignored in `.gitignore`; public feed episodes still live on archive.org.
- `netlify/functions/submission-created.mjs` - runs on every verified submission of the `founding-teams` form
  and emails the sample issue links to the submitter from info@thisismanic.ai via Resend. Every link carries
  a per-submission key (`?k=<submission id>.<HMAC-SHA256>`). The email copy is mirrored in the private repo
  at `outreach/sample-issue-email.md`.
- `netlify/edge-functions/sample-gate.ts` - serves `/sample/*` only to requests with a valid key, or the
  30-day cookie it sets, and shows a 403 page pointing to the form otherwise. Fails closed (503) if the
  secret is missing.
- Environment variables in the Netlify project (all scopes; scoped variables are not available on the
  free plan): `RESEND_API_KEY` (a Resend sending key for thisismanic.ai) and `SAMPLE_LINK_SECRET` (any
  long random string; both functions read it). Optional: `SAMPLE_FROM`, `SAMPLE_REPLY_TO`, `SAMPLE_BCC`.
  Changing a variable needs a new deploy to take effect.

## Files
- `feed.xml` - the RSS feed, newest episode first
- `cover.jpg` - show artwork (3000x3000)
- `index.html` + `assets/` - the thisismanic.ai landing page
- `CNAME` - the custom domain
- `add_episode.py` - publishes an episode (uploads audio, updates the feed)

## Hosting
- **Site and feed:** a push to `main` deploys to Netlify, which serves thisismanic.ai, usually within
  about a minute. The landing page source of truth is `site/index.html` in the private repo: copy it here
  when it changes.
- **Audio:** archive.org, not GitHub Releases. GitHub serves release assets as downloads
  (`application/octet-stream`), which Apple Podcasts refuses to stream. archive.org serves them inline with
  the right audio headers.
- **Old URLs:** `colinmoroney.github.io/manic-mondai-podcast/...` redirects to thisismanic.ai through the
  GitHub Pages custom-domain setting, which is kept only for that redirect.

## Checking the feed
Validate after structural changes at [castfeedvalidator.com](https://castfeedvalidator.com) or
[podba.se/validate](https://podba.se/validate/). Apple Podcasts Connect has a "Refresh Feed" button if a
new episode is slow to appear.
