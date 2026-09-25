# Client meeting weekly intake

Standalone site for collecting weekly client-meeting rows. Do **not** deploy it on the public Digital Assets GitHub Pages site.

## Shared table (what you want)

Everyone opens the **same URL**, clicks **Add meeting**, and rows are saved in one file on the machine running the server. At the end of the week you **Download CSV** or **Download email draft** — that file already has everyone’s updates.

This is not Streamlit. It is the same HTML page, plus a small Python process that writes `data/week.json`.

On a computer teammates can reach (your work PC on the internal network, or an internal server that can run Python):

```bash
py -3 tools/client_meeting_updates/server.py
```

Share `http://<that-machine-name-or-IP>:8765/`. Leave the window running. If you only copy `index.html` onto a file share, there is no shared table — each browser keeps its own rows.

Windows may prompt to allow Python through the firewall; allow it on the private/domain network.

Anyone with the URL can view, edit, delete, and reset the week. There is no login.

## End of week

**Download CSV** or **Download email draft** from the live shared table. When the ISO week rolls (Monday), the server archives last week under `data/backups/` and starts empty. **Start new week** does that on demand (and also downloads a CSV in your browser).

## Email draft

**Download email draft** saves a `.eml` file with `X-Unsent: 1`. Double-click it; Outlook should open an unsent message. Optional default To: copy `js/config.example.js` to `js/config.js` and set `defaultTo`.

## Tests

```bash
py -3 -m pytest tests/test_client_meeting_store.py -q
```
