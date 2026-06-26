/**
 * Smoke test: TMMF Streamlit fullscreen delegation opens modal on expand click.
 * Run: node scripts/verify_tmmf_fullscreen_patch.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const repo = path.resolve(__dirname, "..");
const staticJs = path.join(repo, "static_home", "js");
const tmmfPy = fs.readFileSync(path.join(repo, "streamlit_tmmf_static.py"), "utf8");

const patchMatch = tmmfPy.match(
  /_STREAMLIT_TABLE_FULLSCREEN_IFRAME_VIEWPORT_PATCH = """([\s\S]*?)"""/
);
if (!patchMatch) {
  console.error("Patch block not found in streamlit_tmmf_static.py");
  process.exit(1);
}
const patchJs = patchMatch[1];

const tableFullscreenJs = fs.readFileSync(
  path.join(staticJs, "table-fullscreen.js"),
  "utf8"
);
const tableDownloadJs = fs.readFileSync(
  path.join(staticJs, "table-download.js"),
  "utf8"
);

let modalOpenCount = 0;
let lastTitle = "";

function makeContext() {
  const listeners = [];
  const body = {
    classList: { add() {}, remove() {} },
    _tableFullscreenKeyBound: false,
    appendChild(node) {
      body.children.push(node);
    },
    children: [],
  };

  const modalNodes = new Map();

  const document = {
    body,
    addEventListener(type, fn, capture) {
      listeners.push({ type, fn, capture: !!capture });
    },
    getElementById(id) {
      return modalNodes.get(id) || null;
    },
    createElement(tag) {
      const el = {
        tag,
        id: "",
        className: "",
        hidden: true,
        style: {},
        dataset: {},
        classList: {
          _c: new Set(),
          add(c) {
            this._c.add(c);
          },
          remove(c) {
            this._c.delete(c);
          },
        },
        innerHTML: "",
        children: [],
        appendChild(child) {
          el.children.push(child);
        },
        addEventListener() {},
        querySelector() {
          return null;
        },
        setAttribute() {},
      };
      Object.defineProperty(el, "hidden", {
        get() {
          return el._hidden;
        },
        set(v) {
          el._hidden = v;
        },
      });
      el._hidden = true;
      return el;
    },
  };

  const window = {
    parent: {
      document: { querySelectorAll() { return []; } },
      innerHeight: 800,
      innerWidth: 1200,
      addEventListener() {},
      visualViewport: { offsetTop: 0, offsetLeft: 0, width: 1200, height: 800 },
    },
    frameElement: { getBoundingClientRect: () => ({ top: 0, left: 0, right: 1200, bottom: 800 }) },
    innerWidth: 1200,
    innerHeight: 800,
    addEventListener(type, fn, capture) {
      listeners.push({ type, fn, capture: !!capture });
    },
    __TABLE_FULLSCREEN: null,
    __RWA_STATIC_HELPERS: {},
    __ST_TMMF_FULLSCREEN_PATCHED: false,
    __TMMF_MODAL_OPEN: false,
    document,
    requestAnimationFrame(fn) {
      fn();
    },
  };

  document.defaultView = window;
  window.window = window;
  window.globalThis = window;

  return { window, document, listeners, modalNodes, body };
}

function dispatchClick(listeners, target) {
  const ev = {
    target,
    preventDefault() {},
    stopImmediatePropagation() {
      ev._stopped = true;
    },
    _stopped: false,
  };
  for (const l of listeners) {
    if (l.type !== "click" || !l.capture) continue;
    l.fn(ev);
    if (ev._stopped) break;
  }
  return ev;
}

const ctx = makeContext();
vm.createContext(ctx.window);
vm.runInContext(tableFullscreenJs, ctx.window);
vm.runInContext(tableDownloadJs, ctx.window);
vm.runInContext(patchJs, ctx.window);

const block = {
  classList: { contains(c) { return c === "etp-mock-table-block"; } },
  closest(sel) {
    if (sel.indexOf("etp-mock-table-block") >= 0) return block;
    return null;
  },
  querySelector(sel) {
    if (sel.indexOf("table-wrap") >= 0) return wrap;
    return null;
  },
};

const table = { cloneNode() { return { nodeType: 1, children: [] }; }, getAttribute() { return "Test table"; } };
const wrap = {
  querySelector(sel) {
    if (sel === "table") return table;
    return null;
  },
  getAttribute(name) {
    if (name === "data-fullscreen-title") return "Platforms";
    return null;
  },
  classList: { contains() { return true; } },
};

const expandBtn = {
  disabled: false,
  closest(sel) {
    if (sel.indexOf("etp-mock-table-meta__expand") >= 0) return expandBtn;
    if (sel.indexOf("etp-mock-table-block") >= 0) return block;
    return null;
  },
};

const origOpen = ctx.window.__TABLE_FULLSCREEN.openTableModal;
ctx.window.__TABLE_FULLSCREEN.openTableModal = function (tableEl, opts) {
  modalOpenCount += 1;
  lastTitle = (opts && opts.title) || "";
  origOpen.call(ctx.window.__TABLE_FULLSCREEN, tableEl, opts);
  const modal = ctx.document.getElementById("js-table-fullscreen-modal");
  if (modal) modal.hidden = false;
};

dispatchClick(ctx.listeners, expandBtn);

if (modalOpenCount !== 1) {
  console.error("Expected modal to open once, got", modalOpenCount);
  process.exit(1);
}
if (lastTitle !== "Platforms") {
  console.error("Expected title Platforms, got", lastTitle);
  process.exit(1);
}

const html = fs.readFileSync(path.join(repo, "streamlit_tmmf_static.py"), "utf8");
const bootIdx = html.indexOf("rwa-asset-deep-page.js");
const patchIdx = html.indexOf("st-tmmf-fullscreen-delegation");
if (bootIdx < 0 || patchIdx < 0 || patchIdx < bootIdx) {
  console.error("Patch must load after rwa-asset-deep-page.js");
  process.exit(1);
}

console.log("verify_tmmf_fullscreen_patch: ok");
