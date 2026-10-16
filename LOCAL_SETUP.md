# Local phone evidence setup

Open http://127.0.0.1:8770 to use the installed app.
Double-click `start-local.command` to start it again.

This fork keeps the upstream network editor, map, timeline, evidence view, and reports.
The bridge adds a **Phone archive** tab and opens the current text-led case automatically.
The root page fixes an upstream reference to the missing `src/site/site.js` file.

## Use the app

- Open **Network** to move nodes, edit links, and use graph analysis tools.
- Open **Phone archive** to search records and inspect original text or audio.
- Select **Text-led shortlist** or **Ready transcripts** to find completed audio quickly.
- Click **Add to map** or **Map these results** to merge records without replacing existing edits.
- Click **Find on map** to locate an imported record.
- Double-click a record node and click **Open original record and audio** to inspect its source.
- Click **Process text-led shortlist** to run the existing Jev/Nova-3 queue.

The app uses the existing `crime-stoppers/server.py` on port 8765.
That service reads the existing OpenRouter credential on the server.
The browser and GitHub fork contain no API credential.
The queue retains its existing text-led audio scope and $20 spending cap.
The bridge does not re-transcribe completed recordings.

## Data and saves

The authoritative phone index remains `../crime-stoppers/data/case.sqlite3`.
The bridge does not copy original recordings into Git or the browser case file.
It streams audio from the existing server and retains source record IDs.
The initial board includes the 16 shortlisted recordings, linked texts, and accepted matching calls.
The generated links describe contact metadata, accepted call matches, or Jev review suggestions.
They do not assert speaker identity or shared meaning.

The bridge saves board edits after 1.2 seconds to:
`../crime-stoppers/data/osintcase/working.case.json`.
It preserves the preceding save in `previous.case.json`.
The upstream **Save** button also downloads a portable case file.
Encrypted projects use upstream encrypted saving instead of bridge autosaving.
The earlier local plaintext snapshot remains on disk if you later enable encryption.

The full native case export lives at:
`../crime-stoppers/data/osintcase/archive.case.json`.
**Export full archive** creates a fresh export from the database.
The full export contains all 17,944 records, including automated messages.
The archive browser hides automated messages until you enable its checkbox.

The bridge serves only on 127.0.0.1. Keep both local servers running for source links and playback.
Restart the bridge after editing Python files. Rebuild frontend changes with `npm run build`.

## Verification

Run `python3 -m unittest discover -s bridge -p 'test_*.py' -v`.
Run `npm run build`.
The production dependency audit currently reports zero known vulnerabilities.
Upstream development dependencies still have audit findings.
