// WUJOE shared behavior: mobile nav, scroll reveals, nav scroll-state,
// back-to-top, gallery filters (counts + empty state).

(function () {
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- Mobile nav: animated, closes on link tap / Escape / outside click ----
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    var setMenu = function (open) {
      links.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Menu");
    };
    toggle.addEventListener("click", function () {
      setMenu(!links.classList.contains("open"));
    });
    links.addEventListener("click", function (e) {
      if (e.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && links.classList.contains("open")) {
        setMenu(false);
        toggle.focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (
        links.classList.contains("open") &&
        !e.target.closest(".nav-links") &&
        !e.target.closest(".nav-toggle")
      ) {
        setMenu(false);
      }
    });
  }

  // ---- Scroll-reveal (single + stagger) ----
  var reveals = document.querySelectorAll(".reveal, .reveal-stagger");
  if ("IntersectionObserver" in window && reveals.length) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    reveals.forEach(function (el) { io.observe(el); });

    // Safety net for deep-links and restored scroll positions: anything
    // already at or above the viewport reveals immediately, one-shot.
    var revealInView = function () {
      var vh = window.innerHeight || document.documentElement.clientHeight;
      reveals.forEach(function (el) {
        if (el.classList.contains("is-in")) return;
        var rect = el.getBoundingClientRect();
        if (rect.top < vh && rect.bottom > 0) {
          el.classList.add("is-in");
          io.unobserve(el);
        }
      });
    };
    window.addEventListener("load", revealInView, { once: true });
    window.addEventListener("pageshow", revealInView);
    if (location.hash) setTimeout(revealInView, 80);
  } else {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  }

  // ---- Nav scroll-state via sentinel (no scroll listeners) ----
  var nav = document.querySelector(".nav");
  if (nav && "IntersectionObserver" in window) {
    var navSentinel = document.createElement("div");
    navSentinel.setAttribute("aria-hidden", "true");
    navSentinel.style.cssText =
      "position:absolute;top:0;left:0;width:1px;height:40px;pointer-events:none;";
    document.body.prepend(navSentinel);
    new IntersectionObserver(function (entries) {
      nav.classList.toggle("is-scrolled", !entries[0].isIntersecting);
    }).observe(navSentinel);
  }

  // ---- Back-to-top: injected, shown after the first screenful ----
  if ("IntersectionObserver" in window) {
    var topBtn = document.createElement("button");
    topBtn.className = "back-to-top";
    topBtn.setAttribute("aria-label", "Back to top");
    topBtn.innerHTML =
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    document.body.appendChild(topBtn);

    var topSentinel = document.createElement("div");
    topSentinel.setAttribute("aria-hidden", "true");
    topSentinel.style.cssText =
      "position:absolute;top:0;left:0;width:1px;height:85vh;pointer-events:none;";
    document.body.prepend(topSentinel);
    new IntersectionObserver(function (entries) {
      topBtn.classList.toggle("show", !entries[0].isIntersecting);
    }).observe(topSentinel);

    topBtn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  // ---- Homepage entrance: heading settles in word by word, then letter by
  // letter across the gold accent, with the rest of the hero following ----
  // ---- Homepage entrance: the heading is split so it can settle in word by
  // word, then letter by letter across the gold accent. The animations
  // themselves live in CSS and start on their own; all this does is split the
  // text and hand it over. Anything that throws here still reveals the
  // heading, and if it never runs at all the CSS failsafe reveals it too. ----
  (function heroIntro() {
    var root = document.documentElement;
    if (!root.classList.contains("intro")) return;          // not the homepage
    var hero = document.querySelector(".hero");
    var title = hero && hero.querySelector(".hero-title");
    if (!title) return;

    if (reduceMotion) return;                               // leave it as plain text

    try {
      // The hero has its own arrival; take it out of the scroll-reveal system
      // so the two don't animate the same elements twice.
      [].slice.call(hero.querySelectorAll(".reveal, .reveal-stagger")).forEach(function (el) {
        el.classList.remove("reveal");
        el.classList.remove("reveal-stagger");
      });

      title.setAttribute("aria-label", title.textContent.replace(/\s+/g, " ").trim());

      var order = [];
      var split = function (node, cls) {
        var parts = cls === "l" ? node.textContent.split("")
                                : node.textContent.split(/(\s+)/);
        var frag = document.createDocumentFragment();
        parts.forEach(function (part) {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
          var outer = document.createElement("span");
          outer.className = cls;
          var inner = document.createElement("span");
          inner.textContent = part;
          outer.appendChild(inner);
          frag.appendChild(outer);
          order.push({ el: inner, type: cls });
        });
        node.parentNode.replaceChild(frag, node);
      };

      var walk = function (el, cls) {
        [].slice.call(el.childNodes).forEach(function (n) {
          if (n.nodeType === 3 && n.textContent.trim()) split(n, cls);
          else if (n.nodeType === 1) {
            walk(n, (n.className && String(n.className).indexOf("gold-accent") > -1) ? "l" : cls);
          }
        });
      };
      walk(title, "w");

      var t = 120;
      order.forEach(function (item, i) {
        if (i > 0) t += item.type === "l" ? 26 : 55;
        item.el.style.animationDelay = t + "ms";
      });
      title.classList.add("is-split");
    } catch (e) {
      // Splitting failed; the heading is untouched and still perfectly
      // readable, so there is nothing to recover.
    }
  })();

  // ---- Gallery filters: counts, eased re-entry, empty state ----
  var filters = document.querySelectorAll(".filter-pill");
  var cards = document.querySelectorAll("[data-categories]");
  var gallery = document.querySelector(".gallery");
  if (filters.length && cards.length && gallery) {
    // Count badge per pill
    filters.forEach(function (btn) {
      var cat = btn.dataset.filter;
      var n = 0;
      cards.forEach(function (card) {
        var cats = (card.dataset.categories || "").split(",").map(function (s) { return s.trim(); });
        if (cat === "all" || cats.indexOf(cat) !== -1) n++;
      });
      var badge = document.createElement("span");
      badge.className = "count";
      badge.textContent = n;
      btn.appendChild(badge);
      btn.setAttribute("aria-pressed", btn.classList.contains("active") ? "true" : "false");
    });

    // Empty state with a way back
    var empty = document.createElement("div");
    empty.className = "gallery-empty";
    empty.hidden = true;
    empty.innerHTML =
      "<h3>Nothing in this section yet.</h3>" +
      "<p>We have not published here this issue. Browse the full archive, or pitch us the piece that should fill it.</p>" +
      '<button type="button" class="btn btn-ghost">Show all articles</button>';
    gallery.appendChild(empty);
    empty.querySelector("button").addEventListener("click", function () {
      var allBtn = document.querySelector('.filter-pill[data-filter="all"]');
      if (allBtn) allBtn.click();
    });

    filters.forEach(function (btn) {
      btn.addEventListener("click", function () {
        filters.forEach(function (f) {
          f.classList.remove("active");
          f.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");

        var category = btn.dataset.filter;
        var shown = 0;
        cards.forEach(function (card) {
          var cats = (card.dataset.categories || "").split(",").map(function (s) { return s.trim(); });
          var match = category === "all" || cats.indexOf(category) !== -1;
          card.style.display = match ? "" : "none";
          card.classList.remove("filter-in");
          if (match) {
            shown++;
            // restart the ease-in animation
            void card.offsetWidth;
            card.classList.add("filter-in");
          }
        });
        empty.hidden = shown !== 0;
      });
    });
  }

})();
