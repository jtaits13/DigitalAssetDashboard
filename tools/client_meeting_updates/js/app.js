(function () {
  "use strict";

  const api = window.MeetingUpdates;
  if (!api) {
    throw new Error("MeetingUpdates library failed to load.");
  }

  const config = window.MEETING_UPDATES_CONFIG || { defaultTo: "" };

  const form = document.getElementById("meeting-form");
  const submitBtn = document.getElementById("submit-btn");
  const cancelEdit = document.getElementById("cancel-edit");
  const statusEl = document.getElementById("status");
  const weekChip = document.getElementById("week-chip");
  const emptyState = document.getElementById("empty-state");
  const tableWrap = document.getElementById("table-wrap");
  const tbody = document.getElementById("meetings-body");
  const importFile = document.getElementById("import-file");

  const fields = {
    date: document.getElementById("date"),
    client: document.getElementById("client"),
    purpose: document.getElementById("purpose"),
    owners: document.getElementById("owners"),
    attendees: document.getElementById("attendees"),
  };

  let memoryStore = null;
  let persistWarning = false;
  let editingId = null;
  let statusTimer = null;

  function todayIso() {
    const d = new Date();
    return (
      d.getFullYear() +
      "-" +
      String(d.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(d.getDate()).padStart(2, "0")
    );
  }

  function showStatus(message, kind) {
    statusEl.textContent = message;
    statusEl.className = "status is-visible is-" + (kind || "info");
    if (statusTimer) window.clearTimeout(statusTimer);
    statusTimer = window.setTimeout(function () {
      if (kind !== "warn" && kind !== "error") {
        statusEl.className = "status";
        statusEl.textContent = "";
      }
    }, 8000);
  }

  function readStorage() {
    try {
      const raw = window.localStorage.getItem(api.STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (err) {
      persistWarning = true;
      return memoryStore;
    }
  }

  function writeStorage(store) {
    memoryStore = store;
    try {
      window.localStorage.setItem(api.STORAGE_KEY, JSON.stringify(store));
    } catch (err) {
      persistWarning = true;
    }
  }

  function loadStore() {
    const currentWeekId = api.isoWeekId(new Date());
    const rolled = api.rolloverIfNeeded(readStorage(), currentWeekId);
    if (rolled.previousStore) {
      downloadText(
        api.csvFilename(rolled.previousStore.weekId),
        api.rowsToCsv(rolled.previousStore.rows),
        "text/csv;charset=utf-8"
      );
      writeStorage(rolled.store);
      showStatus(
        "Last week's " +
          rolled.previousStore.rows.length +
          " row(s) were downloaded as CSV and this week started fresh.",
        "info"
      );
      return rolled.store;
    }
    writeStorage(rolled.store);
    return rolled.store;
  }

  function currentStore() {
    return api.parseStore(readStorage()) || api.emptyStore(api.isoWeekId(new Date()));
  }

  function saveRows(rows) {
    const store = currentStore();
    writeStorage({ weekId: store.weekId, rows: rows });
    render();
  }

  function downloadText(filename, content, mime) {
    const blob = new Blob([content], { type: mime || "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  function fallbackCopy(text) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }

  async function copyTable() {
    const rows = currentStore().rows;
    const html = api.rowsToHtmlTable(rows);
    const tsv = api.rowsToTsv(rows);
    try {
      if (navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": new Blob([html], { type: "text/html" }),
            "text/plain": new Blob([tsv], { type: "text/plain" }),
          }),
        ]);
        showStatus("Table copied. Paste it into Outlook or Word.", "ok");
        return;
      }
    } catch (err) {
      // Fall through to plain-text copy.
    }
    const ok = fallbackCopy(tsv);
    showStatus(
      ok ? "Table copied as text." : "Could not copy. Download CSV instead.",
      ok ? "ok" : "error"
    );
  }

  async function copyExcel() {
    const tsv = api.rowsToTsv(currentStore().rows);
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(tsv);
        showStatus("Copied for Excel. Paste into a sheet.", "ok");
        return;
      }
    } catch (err) {
      // Fall through.
    }
    const ok = fallbackCopy(tsv);
    showStatus(
      ok ? "Copied for Excel." : "Could not copy. Download CSV instead.",
      ok ? "ok" : "error"
    );
  }

  function resetForm() {
    editingId = null;
    form.reset();
    fields.date.value = todayIso();
    submitBtn.textContent = "Add meeting";
    cancelEdit.hidden = true;
  }

  function fillForm(row) {
    fields.date.value = row.date;
    fields.client.value = row.client;
    fields.purpose.value = row.purpose;
    fields.owners.value = row.owners;
    fields.attendees.value = row.attendees;
  }

  function render() {
    const store = currentStore();
    const now = new Date();
    weekChip.textContent = api.weekOfLabel(now) + " · " + store.rows.length + " row(s)";
    const rows = api.sortRows(store.rows);
    tbody.replaceChildren();
    if (!rows.length) {
      emptyState.hidden = false;
      tableWrap.hidden = true;
    } else {
      emptyState.hidden = true;
      tableWrap.hidden = false;
      for (const row of rows) {
        const tr = document.createElement("tr");
        const values = [row.date, row.client, row.purpose, row.owners, row.attendees];
        for (const value of values) {
          const td = document.createElement("td");
          td.textContent = value;
          tr.appendChild(td);
        }
        const actions = document.createElement("td");
        actions.className = "actions";
        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "btn-linkish";
        editBtn.textContent = "Edit";
        editBtn.addEventListener("click", function () {
          editingId = row.id;
          fillForm(row);
          submitBtn.textContent = "Save changes";
          cancelEdit.hidden = false;
          fields.client.focus();
          showStatus("Editing this row. Save or cancel when finished.", "info");
        });
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "btn-linkish";
        delBtn.textContent = "Delete";
        delBtn.addEventListener("click", function () {
          if (!window.confirm("Delete this meeting row?")) return;
          saveRows(currentStore().rows.filter(function (item) {
            return item.id !== row.id;
          }));
          if (editingId === row.id) resetForm();
          showStatus("Row deleted.", "ok");
        });
        actions.appendChild(editBtn);
        actions.appendChild(delBtn);
        tr.appendChild(actions);
        tbody.appendChild(tr);
      }
    }
    if (persistWarning) {
      showStatus(
        "This browser blocked local storage, so rows will not persist after you close the tab.",
        "warn"
      );
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const normalized = api.normalizeRow({
      id: editingId || "",
      date: fields.date.value,
      client: fields.client.value,
      purpose: fields.purpose.value,
      owners: fields.owners.value,
      attendees: fields.attendees.value,
    });
    if (!normalized.ok) {
      showStatus("Please fill in: " + normalized.errors.join(", ") + ".", "error");
      return;
    }
    const store = currentStore();
    let rows = store.rows.slice();
    if (editingId) {
      rows = rows.map(function (row) {
        return row.id === editingId ? normalized.row : row;
      });
      showStatus("Row updated.", "ok");
    } else {
      rows.push(normalized.row);
      showStatus("Meeting added.", "ok");
    }
    writeStorage({ weekId: store.weekId, rows: rows });
    resetForm();
    render();
  });

  cancelEdit.addEventListener("click", function () {
    resetForm();
    showStatus("Edit cancelled.", "info");
  });

  document.getElementById("copy-table").addEventListener("click", function () {
    copyTable();
  });
  document.getElementById("copy-excel").addEventListener("click", function () {
    copyExcel();
  });
  document.getElementById("download-csv").addEventListener("click", function () {
    const store = currentStore();
    downloadText(api.csvFilename(store.weekId), api.rowsToCsv(store.rows), "text/csv;charset=utf-8");
    showStatus("CSV downloaded.", "ok");
  });
  document.getElementById("download-eml").addEventListener("click", function () {
    const store = currentStore();
    const now = new Date();
    const eml = api.buildEml({
      to: config.defaultTo || "",
      subject: api.emailSubject(now),
      heading: "Client meetings — " + api.weekOfLabel(now),
      rows: store.rows,
    });
    downloadText(api.emlFilename(store.weekId), eml, "message/rfc822");
    showStatus("Email draft downloaded. Open the .eml file in Outlook to review and send.", "ok");
  });
  document.getElementById("import-btn").addEventListener("click", function () {
    importFile.click();
  });
  importFile.addEventListener("change", function () {
    const file = importFile.files && importFile.files[0];
    importFile.value = "";
    if (!file) return;
    const reader = new FileReader();
    reader.onerror = function () {
      showStatus("Could not read that file.", "error");
    };
    reader.onload = function () {
      try {
        const incoming = api.parseImport(String(reader.result || ""), file.name);
        const merged = api.mergeRows(currentStore().rows, incoming);
        saveRows(merged.rows);
        showStatus(
          "Imported " + merged.addedCount + " new row(s). Duplicates were skipped.",
          "ok"
        );
      } catch (err) {
        showStatus(err.message || "Import failed.", "error");
      }
    };
    reader.readAsText(file);
  });
  document.getElementById("new-week").addEventListener("click", function () {
    const store = currentStore();
    if (!store.rows.length) {
      showStatus("This week is already empty.", "info");
      return;
    }
    const ok = window.confirm(
      "Download a CSV backup and clear this week's table? This cannot be undone except from the backup file."
    );
    if (!ok) return;
    downloadText(api.csvFilename(store.weekId), api.rowsToCsv(store.rows), "text/csv;charset=utf-8");
    writeStorage(api.emptyStore(store.weekId));
    resetForm();
    render();
    showStatus("This week was cleared after a CSV backup download.", "ok");
  });

  resetForm();
  loadStore();
  render();
})();
