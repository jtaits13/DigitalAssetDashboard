# Client meeting weekly intake

Standalone static page for collecting weekly client-meeting rows. Copy this folder onto an internal file server and open `index.html`. Do **not** deploy it on the public Digital Assets GitHub Pages site.

## What it does

People open the page and fill in five fields: Date, Client, Meeting Purpose, Owner(s), and Client Attendee(s). Rows stay in that browser (`localStorage`) for the current Monday–Sunday week.

A static file server cannot keep one shared table for everyone. Each person has their own copy. Typical flow:

1. Teammates add their meetings on the page.
2. They **Copy table** or **Download CSV** and send that to you.
3. You **Import CSV or JSON** to merge their rows, skipping exact duplicates.
4. You **Copy table** into Outlook, or **Download email draft** and open the `.eml` file.

## End of week

When the ISO week changes, the next visit downloads a CSV backup of last week’s rows and starts a fresh table. **Start new week** does the same on demand (backup, then clear).

## Email draft

**Download email draft** saves a `.eml` file with `X-Unsent: 1`. Double-click it on Windows; Outlook should open an unsent message with the HTML table. Optional default To: address:

1. Copy `js/config.example.js` to `js/config.js` (not committed).
2. Set `defaultTo` to your mailbox.

## Local development

```bash
node --test tools/client_meeting_updates/test/lib.test.mjs
```

To click through the page:

```bash
python -m http.server 8765 --directory tools/client_meeting_updates
```

Then open `http://127.0.0.1:8765/`.
