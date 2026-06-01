/**
 * Shared full-screen table modal with horizontal + vertical scroll for wide datasets.
 */
(function (global) {
  var MODAL_ID = "js-table-fullscreen-modal";
  var BODY_ID = "js-table-fullscreen-modal-body";
  var TITLE_ID = "js-table-fullscreen-modal-title";
  var CLOSE_ATTR = "data-table-fullscreen-close";

  function stripElementIds(node) {
    if (!node || node.nodeType !== 1) return;
    node.removeAttribute("id");
    Array.prototype.forEach.call(node.children || [], stripElementIds);
  }

  function closeTableModal() {
    var root = document.getElementById(MODAL_ID);
    if (!root) return;
    root.hidden = true;
    document.body.classList.remove("rwa-table-modal-open");
    var body = document.getElementById(BODY_ID);
    if (body) body.innerHTML = "";
  }

  function ensureTableModal() {
    var root = document.getElementById(MODAL_ID);
    if (root) return root;

    root = document.createElement("div");
    root.id = MODAL_ID;
    root.className = "rwa-table-modal";
    root.hidden = true;
    root.innerHTML =
      '<div class="rwa-table-modal__backdrop" ' +
      CLOSE_ATTR +
      '="1"></div>' +
      '<div class="rwa-table-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="' +
      TITLE_ID +
      '">' +
      '<div class="rwa-table-modal__header">' +
      "<div>" +
      '<p class="rwa-table-modal__eyebrow">Full-screen table</p>' +
      '<h2 class="rwa-table-modal__title" id="' +
      TITLE_ID +
      '">Table</h2>' +
      "</div>" +
      '<button type="button" class="btn btn-secondary rwa-table-modal__close" ' +
      CLOSE_ATTR +
      '="1">Close</button>' +
      "</div>" +
      '<div class="rwa-table-modal__body" id="' +
      BODY_ID +
      '"></div>' +
      "</div>";
    document.body.appendChild(root);

    root.addEventListener("click", function (ev) {
      var closeEl = ev.target.closest ? ev.target.closest("[" + CLOSE_ATTR + "]") : null;
      if (closeEl) closeTableModal();
    });

    if (!document.body._tableFullscreenKeyBound) {
      document.body._tableFullscreenKeyBound = true;
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") closeTableModal();
      });
    }

    return root;
  }

  function openTableModal(tableEl, opts) {
    if (!tableEl) return;
    var root = ensureTableModal();
    var titleEl = document.getElementById(TITLE_ID);
    var body = document.getElementById(BODY_ID);
    if (!root || !titleEl || !body) return;

    titleEl.textContent =
      (opts && opts.title ? String(opts.title) : "") || "Full-screen table";
    body.innerHTML = "";

    var wrap = document.createElement("div");
    wrap.className = "rwa-table-modal__table-wrap";

    var clone = tableEl.cloneNode(true);
    stripElementIds(clone);
    wrap.appendChild(clone);
    body.appendChild(wrap);

    root.hidden = false;
    document.body.classList.add("rwa-table-modal-open");

    var closeBtn = root.querySelector(".rwa-table-modal__close");
    if (closeBtn) closeBtn.focus();
  }

  function createActionButton(cfg) {
    var btn = document.createElement(cfg.tagName === "button" ? "button" : "a");
    btn.className = cfg.className || "btn btn-secondary";
    btn.textContent = cfg.label || "Open";
    if (btn.tagName === "BUTTON") {
      btn.type = "button";
    } else {
      btn.href = cfg.href || "#";
      if (cfg.external) {
        btn.target = "_blank";
        btn.rel = "noopener noreferrer";
      }
    }
    return btn;
  }

  function ensureActionRow(tableWrap, opts) {
    var row = opts && opts.actionRow ? opts.actionRow : null;
    if (!row && tableWrap) {
      var next = tableWrap.nextElementSibling;
      if (next && next.classList && next.classList.contains("rwa-table-actions")) {
        row = next;
      }
    }
    if (!row && tableWrap) {
      row = document.createElement("div");
      row.className = "cta-row rwa-table-actions";
      tableWrap.insertAdjacentElement("afterend", row);
    }
    if (row && row.classList) {
      row.classList.add("rwa-table-actions");
    }
    return row;
  }

  function attachTableFullscreenButton(tableWrap, tableEl, opts) {
    if (!tableWrap || !tableEl || tableWrap._rwaFullscreenBound) return null;
    tableWrap._rwaFullscreenBound = true;

    var actions = ensureActionRow(tableWrap, opts);
    if (!actions) return null;

    var btn = actions.querySelector('[data-rwa-fullscreen-btn="1"]');
    if (!btn) {
      btn = createActionButton({
        tagName: "button",
        className: "btn btn-secondary",
      });
      btn.setAttribute("data-rwa-fullscreen-btn", "1");
      btn.textContent =
        (opts && opts.buttonLabel ? String(opts.buttonLabel) : "") ||
        "View table full screen";
      btn.addEventListener("click", function () {
        openTableModal(tableEl, {
          title: opts && opts.title ? opts.title : "Full-screen table",
        });
      });
      actions.appendChild(btn);
    }
    return actions;
  }

  function appendActionLink(row, cfg) {
    if (!row || !cfg || !cfg.href) return null;
    var key = String(cfg.href).trim() + "::" + String(cfg.label || "").trim();
    var existing = null;
    Array.prototype.forEach.call(row.children || [], function (child) {
      if (!existing && child.getAttribute && child.getAttribute("data-rwa-action-key") === key) {
        existing = child;
      }
    });
    if (existing) return existing;
    var btn = createActionButton({
      className: cfg.className || "btn btn-primary",
      label: cfg.label || "Open",
      href: cfg.href,
      external: cfg.external !== false,
    });
    btn.setAttribute("data-rwa-action-key", key);
    var fullscreenBtn = row.querySelector('[data-rwa-fullscreen-btn="1"]');
    if (fullscreenBtn) row.insertBefore(btn, fullscreenBtn);
    else row.appendChild(btn);
    return btn;
  }

  function wireTablesInContainer(root, opts) {
    var scope = root && root.querySelectorAll ? root : document;
    var selector =
      ".table-wrap--scroll, .rwa-split-table-scroll, .table-wrap table, .table-wrap";
    var seen = new Set();
    scope.querySelectorAll(selector).forEach(function (node) {
      var wrap =
        node.classList &&
        (node.classList.contains("table-wrap") ||
          node.classList.contains("table-wrap--scroll") ||
          node.classList.contains("rwa-split-table-scroll"))
          ? node
          : node.closest
            ? node.closest(".table-wrap--scroll, .rwa-split-table-scroll, .table-wrap")
            : null;
      if (!wrap || seen.has(wrap)) return;
      var table = wrap.querySelector("table");
      if (!table) return;
      seen.add(wrap);
      var title =
        (opts && opts.title) ||
        table.getAttribute("aria-label") ||
        wrap.getAttribute("data-fullscreen-title") ||
        "Full-screen table";
      attachTableFullscreenButton(wrap, table, { title: title });
    });
  }

  var api = {
    closeTableModal: closeTableModal,
    openTableModal: openTableModal,
    attachTableFullscreenButton: attachTableFullscreenButton,
    appendActionLink: appendActionLink,
    wireTablesInContainer: wireTablesInContainer,
  };

  global.__TABLE_FULLSCREEN = api;

  global.__RWA_STATIC_HELPERS = global.__RWA_STATIC_HELPERS || {};
  global.__RWA_STATIC_HELPERS.appendRwaActionLink = appendActionLink;
  global.__RWA_STATIC_HELPERS.attachRwaTableFullscreenButton = function (
    tableWrap,
    tableEl,
    opts
  ) {
    var fs = global.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton) return null;
    return fs.attachTableFullscreenButton(tableWrap, tableEl, opts);
  };
  global.__RWA_STATIC_HELPERS.openRwaTableModal = openTableModal;
  global.__RWA_STATIC_HELPERS.closeRwaTableModal = closeTableModal;
})(typeof window !== "undefined" ? window : this);
