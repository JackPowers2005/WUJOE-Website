// WUJOE article page - TOC active-state tracking + figure lightbox.
// Layered on top of script.js (which handles nav, reveals, progress).

(function () {
  // ---- Table of contents active-section highlight ----
  const tocLinks = Array.from(document.querySelectorAll(".paper-toc a"));
  const sections = tocLinks
    .map((a) => document.querySelector(a.getAttribute("href")))
    .filter(Boolean);

  if (tocLinks.length && sections.length && "IntersectionObserver" in window) {
    const byId = {};
    tocLinks.forEach((a) => (byId[a.getAttribute("href").slice(1)] = a));

    const setActive = (id) => {
      tocLinks.forEach((a) => a.classList.remove("active"));
      if (byId[id]) byId[id].classList.add("active");
    };

    const visible = new Map();
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) visible.set(e.target.id, e.intersectionRatio);
          else visible.delete(e.target.id);
        });
        // pick the topmost currently-visible section
        let best = null;
        let bestTop = Infinity;
        visible.forEach((_, id) => {
          const el = document.getElementById(id);
          if (!el) return;
          const top = el.getBoundingClientRect().top;
          if (top < bestTop) {
            bestTop = top;
            best = id;
          }
        });
        if (best) setActive(best);
      },
      { rootMargin: "-90px 0px -55% 0px", threshold: [0, 0.25, 0.5, 1] }
    );
    sections.forEach((s) => obs.observe(s));
  }

  // Smooth-scroll for TOC clicks (CSS scroll-behavior also covers this;
  // this keeps the active state crisp on click)
  tocLinks.forEach((a) => {
    a.addEventListener("click", () => {
      tocLinks.forEach((x) => x.classList.remove("active"));
      a.classList.add("active");
    });
  });

  // ---- Figure lightbox (with caption) ----
  const lightbox = document.getElementById("lightbox");
  if (lightbox) {
    const lbImg = lightbox.querySelector("img");
    const lbCaption = lightbox.querySelector(".lb-caption");
    const lbClose = lightbox.querySelector(".lb-close");
    const frames = document.querySelectorAll(".figure .frame");

    const open = (src, alt, caption) => {
      lbImg.src = src;
      lbImg.alt = alt || "";
      if (lbCaption) lbCaption.textContent = caption || "";
      lightbox.classList.add("open");
      lightbox.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    };
    const close = () => {
      lightbox.classList.remove("open");
      lightbox.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      lbImg.src = "";
      if (lbCaption) lbCaption.textContent = "";
    };

    frames.forEach((frame) => {
      const img = frame.querySelector("img");
      if (!img) return;
      const fig = frame.closest("figure");
      const cap = fig ? fig.querySelector("figcaption") : null;
      frame.setAttribute("role", "button");
      frame.setAttribute("tabindex", "0");
      frame.setAttribute("aria-label", "Enlarge figure");
      const trigger = () => open(img.src, img.alt, cap ? cap.textContent.trim() : "");
      frame.addEventListener("click", trigger);
      frame.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          trigger();
        }
      });
    });

    lbClose.addEventListener("click", close);
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && lightbox.classList.contains("open")) close();
    });
  }
})();
