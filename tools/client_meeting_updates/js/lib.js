/**
 * Pure helpers for the client-meeting weekly intake page.
 * Works in the browser (global MeetingUpdates) and in Node tests (module.exports).
 */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.MeetingUpdates = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STORAGE_KEY = "client-meeting-updates:v1";
  const COLUMNS = [
    "Date",
    "Client",
    "Meeting Purpose",
    "Owner(s)",
    "Client Attendee(s)",
  ];
  const MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  function newId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return "r" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function localDateOnly(input) {
    if (input instanceof Date) {
      return new Date(input.getFullYear(), input.getMonth(), input.getDate());
    }
    const s = String(input || "").trim();
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (m) {
      return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    }
    const d = new Date(input);
    if (Number.isNaN(d.getTime())) {
      throw new Error("Invalid date");
    }
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  function isoWeekId(input) {
    const local = localDateOnly(input);
    const utc = new Date(Date.UTC(local.getFullYear(), local.getMonth(), local.getDate()));
    const dayNum = utc.getUTCDay() || 7;
    utc.setUTCDate(utc.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil(((utc - yearStart) / 86400000 + 1) / 7);
    return utc.getUTCFullYear() + "-W" + pad2(weekNo);
  }

  function isoWeekMonday(input) {
    const local = localDateOnly(input);
    const day = local.getDay() || 7;
    const monday = new Date(local.getFullYear(), local.getMonth(), local.getDate());
    monday.setDate(monday.getDate() - (day - 1));
    return monday;
  }

  function formatDayMonthYear(input) {
    const d = localDateOnly(input);
    return d.getDate() + " " + MONTHS[d.getMonth()] + " " + d.getFullYear();
  }

  function weekOfLabel(input) {
    return "week of " + formatDayMonthYear(isoWeekMonday(input));
  }

  function emailSubject(input) {
    return "Client meetings - " + weekOfLabel(input);
  }

  function emptyStore(weekId) {
    return { weekId: String(weekId || ""), rows: [] };
  }

  function parseStore(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return null;
    }
    const weekId = String(raw.weekId || "").trim();
    if (!weekId) return null;
    const rows = Array.isArray(raw.rows) ? raw.rows.map(coerceRow).filter(Boolean) : [];
    return { weekId, rows };
  }

  function rolloverIfNeeded(store, currentWeekId) {
    const weekId = String(currentWeekId || "");
    const parsed = parseStore(store);
    if (!parsed) {
      return { store: emptyStore(weekId), previousStore: null };
    }
    if (parsed.weekId === weekId) {
      return { store: parsed, previousStore: null };
    }
    const previousStore = parsed.rows.length ? parsed : null;
    return { store: emptyStore(weekId), previousStore };
  }

  function coerceRow(obj) {
    if (!obj || typeof obj !== "object") return null;
    return {
      id: obj.id ? String(obj.id) : "",
      date: String(obj.date || obj.Date || "").trim(),
      client: String(obj.client || obj.Client || "").trim(),
      purpose: String(
        obj.purpose || obj["Meeting Purpose"] || obj.meetingPurpose || ""
      ).trim(),
      owners: String(obj.owners || obj["Owner(s)"] || obj.Owners || "").trim(),
      attendees: String(
        obj.attendees || obj["Client Attendee(s)"] || obj.Attendees || ""
      ).trim(),
    };
  }

  function normalizeRow(input) {
    const coerced = coerceRow(input) || {
      id: "",
      date: "",
      client: "",
      purpose: "",
      owners: "",
      attendees: "",
    };
    const errors = [];
    if (!/^\d{4}-\d{2}-\d{2}$/.test(coerced.date)) {
      errors.push("Date");
    } else {
      try {
        localDateOnly(coerced.date);
      } catch {
        errors.push("Date");
      }
    }
    if (!coerced.client) errors.push("Client");
    if (!coerced.purpose) errors.push("Meeting Purpose");
    if (!coerced.owners) errors.push("Owner(s)");
    if (!coerced.attendees) errors.push("Client Attendee(s)");
    if (errors.length) {
      return { ok: false, errors };
    }
    return {
      ok: true,
      row: {
        id: coerced.id || newId(),
        date: coerced.date,
        client: coerced.client,
        purpose: coerced.purpose,
        owners: coerced.owners,
        attendees: coerced.attendees,
      },
    };
  }

  function rowSignature(row) {
    const r = coerceRow(row) || {};
    return [r.date, r.client, r.purpose, r.owners, r.attendees]
      .map(function (v) {
        return String(v || "")
          .trim()
          .toLowerCase();
      })
      .join("\0");
  }

  function mergeRows(existing, incoming) {
    const base = Array.isArray(existing) ? existing.slice() : [];
    const seen = new Set(base.map(rowSignature));
    const added = [];
    for (const item of incoming || []) {
      const normalized = normalizeRow(item);
      if (!normalized.ok) continue;
      const sig = rowSignature(normalized.row);
      if (seen.has(sig)) continue;
      seen.add(sig);
      added.push(normalized.row);
    }
    return { rows: base.concat(added), addedCount: added.length };
  }

  function csvEscape(value) {
    const s = String(value ?? "");
    if (/[",\n\r]/.test(s)) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  function rowValues(row) {
    const r = coerceRow(row) || {};
    return [r.date, r.client, r.purpose, r.owners, r.attendees];
  }

  function rowsToCsv(rows) {
    const lines = [COLUMNS.map(csvEscape).join(",")];
    for (const row of rows || []) {
      lines.push(rowValues(row).map(csvEscape).join(","));
    }
    return lines.join("\r\n");
  }

  function rowsToTsv(rows) {
    const clean = function (value) {
      return String(value ?? "")
        .replace(/\t/g, " ")
        .replace(/\r?\n/g, " ");
    };
    const lines = [COLUMNS.join("\t")];
    for (const row of rows || []) {
      lines.push(rowValues(row).map(clean).join("\t"));
    }
    return lines.join("\n");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function rowsToHtmlTable(rows) {
    const body = (rows || [])
      .map(function (row) {
        const cells = rowValues(row)
          .map(function (value) {
            return (
              '<td style="border:1px solid #c7d8e8;padding:6px 10px;vertical-align:top;">' +
              escapeHtml(value).replace(/\n/g, "<br>") +
              "</td>"
            );
          })
          .join("");
        return "<tr>" + cells + "</tr>";
      })
      .join("");
    const head = COLUMNS.map(function (col) {
      return (
        '<th style="border:1px solid #c7d8e8;padding:6px 10px;background:#f0f6fa;text-align:left;">' +
        escapeHtml(col) +
        "</th>"
      );
    }).join("");
    return (
      '<table border="1" cellpadding="6" cellspacing="0" ' +
      'style="border-collapse:collapse;font-family:Calibri,Segoe UI,sans-serif;font-size:12pt;">' +
      "<thead><tr>" +
      head +
      "</tr></thead><tbody>" +
      (body ||
        '<tr><td colspan="5" style="border:1px solid #c7d8e8;padding:6px 10px;">No meetings this week.</td></tr>') +
      "</tbody></table>"
    );
  }

  function encodeQuotedPrintable(input) {
    const bytes = new TextEncoder().encode(String(input ?? ""));
    const lines = [];
    let line = "";
    for (let i = 0; i < bytes.length; i += 1) {
      const b = bytes[i];
      const isSafe = (b >= 33 && b <= 60) || (b >= 62 && b <= 126);
      const token = isSafe
        ? String.fromCharCode(b)
        : "=" + pad2(b.toString(16).toUpperCase());
      if (line.length + token.length > 75) {
        lines.push(line + "=");
        line = token;
      } else {
        line += token;
      }
    }
    if (line) lines.push(line);
    return lines.join("\r\n");
  }

  function buildEml(options) {
    const opts = options || {};
    const to = String(opts.to || "").trim();
    const subject = String(opts.subject || "Client meetings").replace(/[\r\n]/g, " ");
    const heading = String(opts.heading || subject);
    const table = rowsToHtmlTable(opts.rows || []);
    const html =
      "<html><body style=\"font-family:Calibri,Segoe UI,sans-serif;color:#021d41;\">" +
      "<h2 style=\"font-size:16pt;margin:0 0 12px;\">" +
      escapeHtml(heading) +
      "</h2>" +
      table +
      "</body></html>";
    const headers = [
      "X-Unsent: 1",
      to ? "To: " + to : "To: ",
      "Subject: " + subject,
      "MIME-Version: 1.0",
      'Content-Type: text/html; charset="utf-8"',
      "Content-Transfer-Encoding: quoted-printable",
    ];
    return headers.join("\r\n") + "\r\n\r\n" + encodeQuotedPrintable(html);
  }

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let field = "";
    let inQuotes = false;
    const s = String(text || "").replace(/^\uFEFF/, "");
    for (let i = 0; i < s.length; i += 1) {
      const c = s[i];
      if (inQuotes) {
        if (c === '"') {
          if (s[i + 1] === '"') {
            field += '"';
            i += 1;
          } else {
            inQuotes = false;
          }
        } else {
          field += c;
        }
        continue;
      }
      if (c === '"') {
        inQuotes = true;
        continue;
      }
      if (c === ",") {
        row.push(field);
        field = "";
        continue;
      }
      if (c === "\n") {
        row.push(field);
        rows.push(row);
        row = [];
        field = "";
        continue;
      }
      if (c === "\r") {
        continue;
      }
      field += c;
    }
    if (field.length || row.length) {
      row.push(field);
      rows.push(row);
    }
    return rows.filter(function (r) {
      return r.some(function (cell) {
        return String(cell || "").trim() !== "";
      });
    });
  }

  function headerIndexMap(headerRow) {
    const map = {};
    (headerRow || []).forEach(function (name, idx) {
      map[String(name || "").trim().toLowerCase()] = idx;
    });
    function pick(names) {
      for (const name of names) {
        if (Object.prototype.hasOwnProperty.call(map, name)) return map[name];
      }
      return -1;
    }
    return {
      date: pick(["date"]),
      client: pick(["client"]),
      purpose: pick(["meeting purpose", "purpose"]),
      owners: pick(["owner(s)", "owners", "owner"]),
      attendees: pick(["client attendee(s)", "attendees", "client attendees"]),
    };
  }

  function rowsFromCsvMatrix(matrix) {
    if (!matrix.length) return [];
    const idx = headerIndexMap(matrix[0]);
    const hasHeader = idx.date >= 0 && idx.client >= 0;
    const start = hasHeader ? 1 : 0;
    const dateIdx = hasHeader ? idx.date : 0;
    const clientIdx = hasHeader ? idx.client : 1;
    const purposeIdx = hasHeader ? idx.purpose : 2;
    const ownersIdx = hasHeader ? idx.owners : 3;
    const attendeesIdx = hasHeader ? idx.attendees : 4;
    const out = [];
    for (let i = start; i < matrix.length; i += 1) {
      const line = matrix[i];
      const normalized = normalizeRow({
        date: line[dateIdx],
        client: line[clientIdx],
        purpose: line[purposeIdx],
        owners: line[ownersIdx],
        attendees: line[attendeesIdx],
      });
      if (normalized.ok) out.push(normalized.row);
    }
    return out;
  }

  function parseImport(text, filename) {
    const raw = String(text || "");
    const name = String(filename || "").toLowerCase();
    const looksJson =
      name.endsWith(".json") || raw.trim().startsWith("{") || raw.trim().startsWith("[");
    if (looksJson) {
      let data;
      try {
        data = JSON.parse(raw);
      } catch (err) {
        throw new Error("Could not parse JSON import.");
      }
      if (Array.isArray(data)) {
        return data.map(coerceRow).filter(Boolean);
      }
      if (data && Array.isArray(data.rows)) {
        return data.rows.map(coerceRow).filter(Boolean);
      }
      throw new Error("JSON import must be an array of rows or { rows: [...] }.");
    }
    return rowsFromCsvMatrix(parseCsv(raw));
  }

  function csvFilename(weekId) {
    return "client-meetings-" + String(weekId || "week") + ".csv";
  }

  function emlFilename(weekId) {
    return "client-meetings-" + String(weekId || "week") + ".eml";
  }

  function sortRows(rows) {
    return (rows || []).slice().sort(function (a, b) {
      const da = String(a.date || "");
      const db = String(b.date || "");
      if (da !== db) return da < db ? -1 : 1;
      const ca = String(a.client || "").toLowerCase();
      const cb = String(b.client || "").toLowerCase();
      if (ca !== cb) return ca < cb ? -1 : 1;
      return String(a.id || "").localeCompare(String(b.id || ""));
    });
  }

  return {
    STORAGE_KEY,
    COLUMNS,
    newId,
    isoWeekId,
    isoWeekMonday,
    formatDayMonthYear,
    weekOfLabel,
    emailSubject,
    emptyStore,
    parseStore,
    rolloverIfNeeded,
    coerceRow,
    normalizeRow,
    rowSignature,
    mergeRows,
    csvEscape,
    rowsToCsv,
    rowsToTsv,
    escapeHtml,
    rowsToHtmlTable,
    encodeQuotedPrintable,
    buildEml,
    parseCsv,
    parseImport,
    csvFilename,
    emlFilename,
    sortRows,
  };
});
