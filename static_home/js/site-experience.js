/**
 * Site experience UX: header elevation (all pages); home scroll reveal + jump nav.
 */
(function () {
  if (!document.body.classList.contains("site-experience")) return;

  var isHome = document.body.classList.contains("page-home");
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initReveal() {
    var nodes = document.querySelectorAll(".home-reveal");
    if (!nodes.length) return;

    if (reducedMotion || !("IntersectionObserver" in window)) {
      nodes.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { root: null, rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    nodes.forEach(function (el) {
      observer.observe(el);
    });
  }

  function initJumpNav() {
    var links = Array.prototype.slice.call(
      document.querySelectorAll(".home-jump-nav__link[href^='#']")
    );
    if (!links.length) return;

    var sections = links
      .map(function (link) {
        var id = link.getAttribute("href").slice(1);
        var section = document.getElementById(id);
        return section ? { link: link, section: section } : null;
      })
      .filter(Boolean);

    if (!sections.length) return;

    function setActive(id) {
      sections.forEach(function (item) {
        var on = item.section.id === id;
        item.link.classList.toggle("is-active", on);
        if (on) item.link.setAttribute("aria-current", "true");
        else item.link.removeAttribute("aria-current");
      });
    }

    links.forEach(function (link) {
      link.addEventListener("click", function (ev) {
        var href = link.getAttribute("href");
        if (!href || href.charAt(0) !== "#") return;
        var target = document.getElementById(href.slice(1));
        if (!target) return;
        ev.preventDefault();
        target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
        history.replaceState(null, "", href);
        setActive(target.id);
      });
    });

    if (!("IntersectionObserver" in window)) return;

    var navObserver = new IntersectionObserver(
      function (entries) {
        var visible = entries
          .filter(function (e) {
            return e.isIntersecting;
          })
          .sort(function (a, b) {
            return b.intersectionRatio - a.intersectionRatio;
          });
        if (visible.length) setActive(visible[0].target.id);
      },
      { root: null, rootMargin: "-35% 0px -55% 0px", threshold: [0, 0.15, 0.4] }
    );

    sections.forEach(function (item) {
      navObserver.observe(item.section);
    });
  }

  function watchNewsList() {
    var list = document.getElementById("js-home-news-list");
    if (!list || list._hxAnimatedWatch) return;
    list._hxAnimatedWatch = true;

    function maybeAnimate() {
      if (list.querySelector(".headline-list__loading, .headline-list__empty")) return;
      list.classList.add("headline-list--animated");
    }

    maybeAnimate();
    if ("MutationObserver" in window) {
      var mo = new MutationObserver(maybeAnimate);
      mo.observe(list, { childList: true, subtree: true });
    }
  }

  function initHeaderScroll() {
    var header = document.querySelector(".site-header");
    if (!header) return;
    function onScroll() {
      header.classList.toggle("site-header--elevated", window.scrollY > 6);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function init() {
    initHeaderScroll();
    if (!isHome) return;
    initReveal();
    initJumpNav();
    watchNewsList();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
