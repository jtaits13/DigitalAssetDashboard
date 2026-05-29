/**
 * Download table data as .xlsx (SheetJS loaded on first use).
 */
(function (global) {
  var XLSX_CDN =
    "https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js";
  var xlsxPromise = null;

  var DOWNLOAD_ICON =
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>';

  function loadXlsx() {
    if (global.XLSX) return Promise.resolve(global.XLSX);
    if (xlsxPromise) return xlsxPromise;
    xlsxPromise = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = XLSX_CDN;
      script.async = true;
      script.onload = function () {
        if (global.XLSX) resolve(global.XLSX);
        else reject(new Error("SheetJS failed to load"));
      };
      script.onerror = function () {
        reject(new Error("Could not load SheetJS"));
      };
      document.head.appendChild(script);
    });
    return xlsxPromise;
  }

  function slugFilename(name) {
    return (
      String(name || "table")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || "table"
    );
  }

  function cellText(td) {
    if (!td) return "";
    var link = td.querySelector("a[href]");
    if (link) {
      var label = link.textContent.replace(/\s+/g, " ").trim();
      if (label === "↗" || label === "Open" || label === "Filing") {
        return link.getAttribute("href") || label;
      }
      return label;
    }
    return td.textContent.replace(/\s+/g, " ").trim();
  }

  function extractFromTable(tableEl) {
    if (!tableEl) return { headers: [], rows: [] };
    var headers = [];
    var thead = tableEl.querySelector("thead");
    if (thead) {
      thead.querySelectorAll("th").forEach(function (th) {
        var label = th.textContent.replace(/\s+/g, " ").trim();
        headers.push(label === "↗" ? "Link" : label);
      });
    }
    var rows = [];
    tableEl.querySelectorAll("tbody tr").forEach(function (tr) {
      var cells = tr.querySelectorAll("td");
      if (!cells.length) return;
      if (cells.length === 1 && cells[0].hasAttribute("colspan")) return;
      var row = [];
      cells.forEach(function (td) {
        row.push(cellText(td));
      });
      rows.push(row);
    });
    return { headers: headers, rows: rows };
  }

  function resolveExportData(tableEl, opts) {
    if (opts && typeof opts.getExportData === "function") {
      var custom = opts.getExportData(tableEl);
      if (custom && custom.headers && custom.rows) return custom;
    }
    return extractFromTable(tableEl);
  }

  function downloadXlsx(data, filename) {
    return loadXlsx().then(function (XLSX) {
      var headers = data.headers || [];
      var rows = data.rows || [];
      if (!headers.length || !rows.length) {
        throw new Error("No table rows to export");
      }
      var sheetName =
        (data.sheetName && String(data.sheetName).slice(0, 31)) || "Data";
      var ws = XLSX.utils.aoa_to_sheet([headers].concat(rows));
      var wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, sheetName);
      XLSX.writeFile(wb, slugFilename(filename) + ".xlsx");
    });
  }

  function triggerDownload(tableEl, opts) {
    var data = resolveExportData(tableEl, opts);
    if (!data.rows || !data.rows.length) {
      return Promise.reject(new Error("No table rows to export"));
    }
    var filename =
      (opts && opts.filename) ||
      (opts && opts.title) ||
      tableEl.getAttribute("aria-label") ||
      "table";
    return downloadXlsx(data, filename);
  }

  function ensureExportBar(tableWrap) {
    var existing = tableWrap.previousElementSibling;
    if (
      existing &&
      existing.classList &&
      existing.classList.contains("table-export-bar")
    ) {
      return existing;
    }
    var bar = document.createElement("div");
    bar.className = "table-export-bar";
    tableWrap.parentNode.insertBefore(bar, tableWrap);
    return bar;
  }

  function attachTableDownloadButton(tableWrap, tableEl, opts) {
    if (!tableWrap || !tableEl || tableWrap._rwaDownloadBound) return null;
    tableWrap._rwaDownloadBound = true;
    tableWrap._rwaDownloadOpts = opts || {};

    var bar = ensureExportBar(tableWrap);
    var btn = bar.querySelector('[data-table-download-btn="1"]');
    if (btn) return bar;

    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "table-download-btn";
    btn.setAttribute("data-table-download-btn", "1");
    btn.setAttribute("aria-label", "Download table as Excel");
    btn.title = "Download as Excel (.xlsx)";
    btn.innerHTML = DOWNLOAD_ICON;
    btn.addEventListener("click", function () {
      btn.disabled = true;
      btn.classList.add("is-loading");
      triggerDownload(tableEl, tableWrap._rwaDownloadOpts)
        .catch(function (err) {
          console.error("Table download failed", err);
          if (global.alert) {
            global.alert("Could not download the table. Please try again.");
          }
        })
        .finally(function () {
          btn.disabled = false;
          btn.classList.remove("is-loading");
        });
    });
    bar.appendChild(btn);
    return bar;
  }

  function patchFullscreenAttach() {
    var fs = global.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton || fs._downloadPatched) return;
    fs._downloadPatched = true;
    var origAttach = fs.attachTableFullscreenButton;
    fs.attachTableFullscreenButton = function (tableWrap, tableEl, opts) {
      attachTableDownloadButton(tableWrap, tableEl, opts);
      return origAttach(tableWrap, tableEl, opts);
    };
  }

  patchFullscreenAttach();

  var api = {
    attachTableDownloadButton: attachTableDownloadButton,
    downloadTableXlsx: triggerDownload,
    extractFromTable: extractFromTable,
  };

  global.__TABLE_DOWNLOAD = api;

  global.__RWA_STATIC_HELPERS = global.__RWA_STATIC_HELPERS || {};
  global.__RWA_STATIC_HELPERS.attachRwaTableDownloadButton =
    attachTableDownloadButton;
})(typeof window !== "undefined" ? window : this);
