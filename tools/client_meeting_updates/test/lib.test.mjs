import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const lib = require("../js/lib.js");

test("isoWeekId uses Monday-Sunday ISO weeks", () => {
  assert.equal(lib.isoWeekId("2026-09-21"), "2026-W39");
  assert.equal(lib.isoWeekId("2026-09-25"), "2026-W39");
  assert.equal(lib.isoWeekId("2026-09-27"), "2026-W39");
  assert.equal(lib.isoWeekId("2026-09-28"), "2026-W40");
  assert.equal(lib.isoWeekId("2021-01-01"), "2020-W53");
  assert.equal(lib.isoWeekId("2021-01-04"), "2021-W01");
});

test("week label is the Monday of the ISO week", () => {
  assert.equal(lib.weekOfLabel("2026-09-25"), "week of 21 Sep 2026");
  assert.equal(
    lib.emailSubject("2026-09-25"),
    "Client meetings - week of 21 Sep 2026"
  );
});

test("rolloverIfNeeded clears stale weeks and keeps the previous store", () => {
  const stale = {
    weekId: "2026-W38",
    rows: [
      {
        id: "1",
        date: "2026-09-16",
        client: "Acme",
        purpose: "Intro",
        owners: "Alex",
        attendees: "Pat",
      },
    ],
  };
  const rolled = lib.rolloverIfNeeded(stale, "2026-W39");
  assert.equal(rolled.store.weekId, "2026-W39");
  assert.deepEqual(rolled.store.rows, []);
  assert.equal(rolled.previousStore.weekId, "2026-W38");
  assert.equal(rolled.previousStore.rows.length, 1);

  const same = lib.rolloverIfNeeded(stale, "2026-W38");
  assert.equal(same.previousStore, null);
  assert.equal(same.store.rows.length, 1);

  const emptyOld = lib.rolloverIfNeeded({ weekId: "2026-W38", rows: [] }, "2026-W39");
  assert.equal(emptyOld.previousStore, null);
  assert.equal(emptyOld.store.weekId, "2026-W39");
});

test("CSV round-trips commas, quotes, and newlines", () => {
  const rows = [
    {
      date: "2026-09-22",
      client: 'Acme, "North"',
      purpose: "Kickoff\nFollow-up",
      owners: "Alex",
      attendees: "Pat, Sam",
    },
  ];
  const csv = lib.rowsToCsv(rows);
  assert.match(csv, /^Date,Client,Meeting Purpose,Owner\(s\),Client Attendee\(s\)\r\n/);
  assert.match(csv, /"Acme, ""North"""/);
  const parsed = lib.parseImport(csv, "week.csv");
  assert.equal(parsed.length, 1);
  assert.equal(parsed[0].client, 'Acme, "North"');
  assert.equal(parsed[0].purpose, "Kickoff\nFollow-up");
  assert.equal(parsed[0].attendees, "Pat, Sam");
});

test("buildEml writes an unsent Outlook draft with the table", () => {
  const eml = lib.buildEml({
    to: "reviewer@example.com",
    subject: "Client meetings - week of 21 Sep 2026",
    heading: "Client meetings — week of 21 Sep 2026",
    rows: [
      {
        date: "2026-09-22",
        client: "Acme",
        purpose: "Intro",
        owners: "Alex",
        attendees: "Pat",
      },
    ],
  });
  assert.ok(eml.startsWith("X-Unsent: 1\r\n"));
  assert.match(eml, /To: reviewer@example.com/);
  assert.match(eml, /Subject: Client meetings - week of 21 Sep 2026/);
  assert.match(eml, /Content-Transfer-Encoding: quoted-printable/);
  assert.match(eml, /Acme/);
  assert.match(eml, /<table/);
});

test("mergeRows skips exact duplicates and keeps new meetings", () => {
  const existing = [
    {
      id: "a",
      date: "2026-09-22",
      client: "Acme",
      purpose: "Intro",
      owners: "Alex",
      attendees: "Pat",
    },
  ];
  const incoming = [
    existing[0],
    {
      date: "2026-09-23",
      client: "Beta",
      purpose: "Review",
      owners: "Sam",
      attendees: "Jo",
    },
  ];
  const merged = lib.mergeRows(existing, incoming);
  assert.equal(merged.addedCount, 1);
  assert.equal(merged.rows.length, 2);
  assert.equal(merged.rows[1].client, "Beta");
});

test("HTML export escapes markup", () => {
  const html = lib.rowsToHtmlTable([
    {
      date: "2026-09-22",
      client: "<script>x</script>",
      purpose: "A & B",
      owners: "Alex",
      attendees: "Pat",
    },
  ]);
  assert.equal(html.includes("<script>"), false);
  assert.match(html, /&lt;script&gt;x&lt;\/script&gt;/);
  assert.match(html, /A &amp; B/);
});

test("parseImport accepts JSON row arrays", () => {
  const json = JSON.stringify({
    weekId: "2026-W39",
    rows: [
      {
        Date: "2026-09-24",
        Client: "Gamma",
        "Meeting Purpose": "Update",
        "Owner(s)": "Riley",
        "Client Attendee(s)": "Chris",
      },
    ],
  });
  const parsed = lib.parseImport(json, "week.json");
  assert.equal(parsed.length, 1);
  assert.equal(parsed[0].client, "Gamma");
  assert.equal(parsed[0].owners, "Riley");
});

test("normalizeRow requires every column", () => {
  const missing = lib.normalizeRow({
    date: "2026-09-22",
    client: "Acme",
    purpose: "",
    owners: "Alex",
    attendees: "Pat",
  });
  assert.equal(missing.ok, false);
  assert.deepEqual(missing.errors, ["Meeting Purpose"]);
});
