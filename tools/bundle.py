#!/usr/bin/env python3
"""Bundle the multi-page WUJOE site into one self-contained HTML file.

An Artifact is a single file at a single URL, so the 7 pages become hash
routes behind one shared nav and footer. Everything is inlined: the
stylesheet, the fonts (see fetch_fonts.py) and every image as a data URI.

    python3 fetch_fonts.py    # once, writes fonts.css
    python3 bundle.py         # writes wujoe-share.html

Then publish wujoe-share.html as an Artifact, passing the existing URL so the
link stays the same.
"""
import base64, io, os, re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_site(start):
    """Locate the site root (the folder holding index.html).

    Works both from wujoe-build/ next to wujoe-website/, and from a checkout
    where this script lives in tools/ and the site sits at the repo root.
    """
    d = start
    for _ in range(3):
        if os.path.isfile(os.path.join(d, "index.html")):
            return d
        sib = os.path.join(d, "wujoe-website")
        if os.path.isfile(os.path.join(sib, "index.html")):
            return sib
        d = os.path.dirname(d)
    raise SystemExit("bundle.py: could not find the site (no index.html found)")


SITE = _find_site(os.path.dirname(HERE))
OUT = os.path.join(HERE, "wujoe-share.html")

ROUTES = [                       # slug, source file, nav label it activates
    ("home",       "index.html",                                     "Home"),
    ("articles",   "articles.html",                                  "Articles"),
    ("leadership", "leadership.html",                                "Leadership"),
    ("stablecoin", "articles/stablecoin-digital-dollarization.html", "Articles"),
    ("ai",         "articles/ai-midwestern-markets.html",            "Articles"),
    # TEMPORARILY WITHDRAWN -- the school-funding review is not published on the
    # site right now; re-enable this route (and the two link entries below) when
    # the authors finish their revision.
    # ("schools",    "articles/stl-school-funding.html",               "Articles"),
    ("hb3231",     "articles/hb3231-st-louis.html",                  "Articles"),
]
LINKMAP = {
    "index.html": "#/home", "articles.html": "#/articles", "leadership.html": "#/leadership",
    "articles/stablecoin-digital-dollarization.html": "#/stablecoin",
    "articles/ai-midwestern-markets.html": "#/ai",
    # "articles/stl-school-funding.html": "#/schools",   # TEMPORARILY WITHDRAWN
    "articles/hb3231-st-louis.html": "#/hb3231",
    "stablecoin-digital-dollarization.html": "#/stablecoin",
    "ai-midwestern-markets.html": "#/ai",
    # "stl-school-funding.html": "#/schools",            # TEMPORARILY WITHDRAWN
    "hb3231-st-louis.html": "#/hb3231",
}
LINK_KEYS = sorted(LINKMAP, key=len, reverse=True)   # "articles/x.html" before "articles.html"

MAXW = {"team": 620, "figs": 1000, "photo": 1200}
_cache = {}


def data_uri(rel):
    if rel in _cache:
        return _cache[rel]
    path = os.path.join(SITE, rel)
    ext = os.path.splitext(rel)[1].lower()
    if ext == ".svg":
        uri = "data:image/svg+xml;base64," + base64.b64encode(open(path, "rb").read()).decode()
    else:
        im = Image.open(path)
        cap = (MAXW["team"] if "/team/" in rel
               else MAXW["figs"] if re.search(r"(fig\d|topics)", rel)
               else MAXW["photo"])
        if im.width > cap:
            im = im.resize((cap, round(im.height * cap / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=86, optimize=True, progressive=True)
        uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    _cache[rel] = uri
    print(f"    inlined {rel:44} {len(uri)/1024:7.0f} KB")
    return uri


def drop_withdrawn(html):
    """Remove blocks the site has commented out as TEMPORARILY WITHDRAWN.

    They stay in the page source so they are trivial to restore, but the
    published bundle should not carry an unpublished article's copy -- or pay
    to inline its thumbnail.
    """
    return re.sub(r"[ \t]*<!--\s*TEMPORARILY WITHDRAWN.*?-->\s*", "\n", html, flags=re.S)


def inline_images(html):
    def rep(m):
        rel = re.sub(r"^\.\./", "", m.group(2))
        rel = rel.split("?", 1)[0]        # drop the cache-busting ?v= before resolving
        if not os.path.exists(os.path.join(SITE, rel)):
            return m.group(0)
        return m.group(1) + data_uri(rel) + m.group(3)
    return re.sub(r'(src=")((?:\.\./)?assets/[^"]+)(")', rep, html)


def namespace_ids(html, slug):
    """Both papers use #introduction/#conclusion/#references and every page has
    #main. Prefix ids per route so they stay unique, and send in-page anchors
    through the router instead of the browser's native (now broken) jump."""
    html = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{slug}-{m.group(1)}"', html)
    html = re.sub(r'href="#([^"/][^"]*)"', lambda m: f'href="#/{slug}|{m.group(1)}"', html)
    # SVG paint servers and aria references point at ids too, so they have to
    # follow the rename or the hero chart loses its gradient fill.
    html = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{slug}-{m.group(1)})', html)
    html = re.sub(r'aria-labelledby="([^"]+)"',
                  lambda m: 'aria-labelledby="' + ' '.join(slug + '-' + t for t in m.group(1).split()) + '"',
                  html)
    return html


def rewrite_links(html):
    def rep(m):
        raw = m.group(1)
        if raw.startswith(("http", "mailto:", "#", "data:")):
            return m.group(0)
        base, _, frag = raw.partition("#")
        base = re.sub(r"^\.\./", "", base)
        for k in LINK_KEYS:
            if base == k:
                return 'href="' + LINKMAP[k] + (("|" + frag) if frag else "") + '"'
        return m.group(0)
    return re.sub(r'href="([^"]+)"', rep, html)


JS = r"""
(function () {
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var routes = [].slice.call(document.querySelectorAll('.route'));

  var toggle = document.querySelector('.nav-toggle'), links = document.querySelector('.nav-links');
  function setMenu(o){ links.classList.toggle('open', o);
    toggle.setAttribute('aria-expanded', o?'true':'false');
    toggle.setAttribute('aria-label', o?'Close menu':'Menu'); }
  toggle.addEventListener('click', function(){ setMenu(!links.classList.contains('open')); });
  links.addEventListener('click', function(e){ if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') setMenu(false); });

  var nav = document.querySelector('.nav');
  var topBtn = document.createElement('button');
  topBtn.className = 'back-to-top'; topBtn.setAttribute('aria-label','Back to top');
  topBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
  document.body.appendChild(topBtn);
  topBtn.addEventListener('click', function(){ scrollTo({top:0, behavior: reduce?'auto':'smooth'}); });
  addEventListener('scroll', function(){
    nav.classList.toggle('is-scrolled', scrollY > 40);
    topBtn.classList.toggle('show', scrollY > innerHeight * 0.85);
  }, {passive:true});

  function reveals(root){
    var els = [].slice.call(root.querySelectorAll('.reveal, .reveal-stagger'));
    if (!('IntersectionObserver' in window)) { els.forEach(function(e){e.classList.add('is-in');}); return; }
    var io = new IntersectionObserver(function(en){
      en.forEach(function(x){ if(x.isIntersecting){ x.target.classList.add('is-in'); io.unobserve(x.target); } });
    }, {threshold:0.08, rootMargin:'0px 0px -6% 0px'});
    els.forEach(function(e){ io.observe(e); });
    var vh = innerHeight;
    els.forEach(function(e){ var r = e.getBoundingClientRect();
      if (r.top < vh && r.bottom > 0) { e.classList.add('is-in'); io.unobserve(e); } });
  }

  function filters(root){
    var pills = root.querySelectorAll('.filter-pill'),
        cards = root.querySelectorAll('[data-categories]'),
        gallery = root.querySelector('.gallery');
    if (!pills.length || !gallery || root.dataset.filtersReady) return;
    root.dataset.filtersReady = '1';
    pills.forEach(function(b){
      var cat = b.dataset.filter, n = 0;
      cards.forEach(function(c){
        var l = (c.dataset.categories||'').split(',').map(function(s){return s.trim();});
        if (cat === 'all' || l.indexOf(cat) !== -1) n++;
      });
      var badge = document.createElement('span');
      badge.className = 'count'; badge.textContent = n; b.appendChild(badge);
      b.setAttribute('aria-pressed', b.classList.contains('active') ? 'true' : 'false');
    });
    var empty = document.createElement('div');
    empty.className = 'gallery-empty'; empty.hidden = true;
    empty.innerHTML = '<h3>Nothing in this section yet.</h3><p>Browse the full archive instead.</p>' +
      '<button type="button" class="btn btn-ghost">Show all articles</button>';
    gallery.appendChild(empty);
    empty.querySelector('button').addEventListener('click', function(){
      root.querySelector('.filter-pill[data-filter="all"]').click(); });
    pills.forEach(function(b){
      b.addEventListener('click', function(){
        pills.forEach(function(p){ p.classList.remove('active'); p.setAttribute('aria-pressed','false'); });
        b.classList.add('active'); b.setAttribute('aria-pressed','true');
        var cat = b.dataset.filter, shown = 0;
        cards.forEach(function(c){
          var l = (c.dataset.categories||'').split(',').map(function(s){return s.trim();});
          var hit = cat === 'all' || l.indexOf(cat) !== -1;
          c.style.display = hit ? '' : 'none';
          c.classList.remove('filter-in');
          if (hit) { shown++; void c.offsetWidth; c.classList.add('filter-in'); }
        });
        empty.hidden = shown !== 0;
      });
    });
  }

  var tocObs = null;
  function toc(root){
    if (tocObs) { tocObs.disconnect(); tocObs = null; }
    var tocEl = root.querySelector('.paper-toc');
    if (!tocEl) return;
    var slug = root.id.replace('route-','');
    var anchors = [].slice.call(tocEl.querySelectorAll('a'));
    var secs = anchors.map(function(a){
      return document.getElementById(slug + '-' + a.getAttribute('href').split('|').pop());
    });
    var visible = new Set();
    tocObs = new IntersectionObserver(function(en){
      en.forEach(function(x){ x.isIntersecting ? visible.add(x.target) : visible.delete(x.target); });
      var best = null;
      secs.forEach(function(s){ if (s && visible.has(s) && !best) best = s; });
      if (best) anchors.forEach(function(a, i){ a.classList.toggle('active', secs[i] === best); });
    }, {rootMargin:'-90px 0px -55% 0px'});
    secs.forEach(function(s){ if (s) tocObs.observe(s); });
  }

  var lb = document.getElementById('lightbox');
  if (lb) {
    var lbImg = lb.querySelector('img'), lbCap = lb.querySelector('.lb-caption');
    var close = function(){ lb.classList.remove('open'); lb.setAttribute('aria-hidden','true'); };
    document.addEventListener('click', function(e){
      var fig = e.target.closest('.figure .frame img');
      if (fig) { lbImg.src = fig.src; lbImg.alt = fig.alt || '';
        var cap = fig.closest('figure') && fig.closest('figure').querySelector('figcaption');
        lbCap.textContent = cap ? cap.textContent.trim() : '';
        lb.classList.add('open'); lb.setAttribute('aria-hidden','false'); return; }
      if (e.target.closest('.lb-close') || e.target === lb) close();
    });
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape') close(); });
  }

  // ---- Homepage entrance (mirrors script.js on the real site).
  // The animations live in CSS and start on their own; this only splits the
  // heading. Anything that throws still reveals it, and a CSS failsafe covers
  // the case where this never runs. ----
  var introDone = false;
  function heroIntro(root){
    if (introDone) return;
    introDone = true;
    var hero = root.querySelector('.hero');
    var title = hero && hero.querySelector('.hero-title');
    if (!title) return;

    if (reduce) return;                       // leave it as plain text

    try {
      [].slice.call(hero.querySelectorAll('.reveal, .reveal-stagger')).forEach(function(el){
        el.classList.remove('reveal');
        el.classList.remove('reveal-stagger');
        el.classList.add('is-in');
      });
      title.setAttribute('aria-label', title.textContent.replace(/\s+/g, ' ').trim());

      var order = [];
      var split = function(node, cls){
        var parts = cls === 'l' ? node.textContent.split('') : node.textContent.split(/(\s+)/);
        var frag = document.createDocumentFragment();
        parts.forEach(function(part){
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
          var outer = document.createElement('span'); outer.className = cls;
          var inner = document.createElement('span'); inner.textContent = part;
          outer.appendChild(inner); frag.appendChild(outer);
          order.push({ el: inner, type: cls });
        });
        node.parentNode.replaceChild(frag, node);
      };
      var walk = function(el, cls){
        [].slice.call(el.childNodes).forEach(function(n){
          if (n.nodeType === 3 && n.textContent.trim()) split(n, cls);
          else if (n.nodeType === 1) {
            walk(n, (n.className && String(n.className).indexOf('gold-accent') > -1) ? 'l' : cls);
          }
        });
      };
      walk(title, 'w');

      var t = 120;
      order.forEach(function(item, i){
        if (i > 0) t += item.type === 'l' ? 26 : 55;
        item.el.style.animationDelay = t + 'ms';
      });
      title.classList.add('is-split');
    } catch (e) {
      // Splitting failed; the heading is untouched and still readable.
    }
  }

  function show(slug, frag){
    var el = document.getElementById('route-' + slug) || routes[0];
    routes.forEach(function(r){ r.hidden = (r !== el); });
    document.querySelectorAll('.nav-links a').forEach(function(a){
      var on = a.textContent.trim() === el.dataset.nav;
      a.classList.toggle('active', on);
      on ? a.setAttribute('aria-current','page') : a.removeAttribute('aria-current');
    });
    reveals(el); filters(el); toc(el);
    if (slug === 'home') heroIntro(el);
    if (frag) {
      var t = document.getElementById(slug + '-' + frag);
      if (t) {
        // Images decode after the route is shown, which changes the document
        // height and drops an early scroll. Keep re-anchoring until the
        // target's position holds still twice, or we run out of patience.
        var last = null, tries = 0;
        var settle = function(){
          t.scrollIntoView();
          var top = Math.round(t.getBoundingClientRect().top);
          if (top === last && tries > 1) return;
          last = top;
          if (++tries < 14) setTimeout(settle, 120);
        };
        // setTimeout, not rAF: rAF is paused in a background tab, so a
        // link opened in one would never scroll to its section.
        setTimeout(settle, 0);
        return;
      }
    }
    scrollTo(0, 0);
  }
  function route(){
    var parts = location.hash.replace(/^#\/?/, '').split('|');
    show(parts[0] || 'home', parts[1]);
  }
  addEventListener('hashchange', route);
  route();
})();
"""


def build():
    fonts = open(os.path.join(HERE, "fonts.css"), encoding="utf-8").read()
    css = open(os.path.join(SITE, "styles.css"), encoding="utf-8").read()
    src0 = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()

    nav = rewrite_links(re.search(r'(  <header class="nav">.*?</header>)', src0, re.S).group(1))
    footer = rewrite_links(re.search(r'(  <footer class="footer">.*?</footer>)', src0, re.S).group(1))

    routes_html, lightbox = [], ""
    for slug, f, label in ROUTES:
        print(f"  route /{slug}")
        s = open(os.path.join(SITE, f), encoding="utf-8").read()
        body = s[s.find("</header>") + len("</header>"): s.find("<!-- Footer -->")]
        if not lightbox:
            m = re.search(r'(  <div class="lightbox".*?</div>\s*</figure>\s*</div>)', s, re.S)
            if m:
                lightbox = m.group(1)
        body = body.replace(' loading="lazy"', '')   # data URIs; lazy only hides layout height
        body = rewrite_links(inline_images(namespace_ids(drop_withdrawn(body), slug)))
        routes_html.append(
            f'<div class="route" id="route-{slug}" data-nav="{label}" hidden>\n{body}\n</div>')

    nav, footer = inline_images(drop_withdrawn(nav)), inline_images(drop_withdrawn(footer))

    doc = f"""<style>
{fonts}

{css}
/* --- bundle-only: single-file routing --- */
.route[hidden] {{ display: none; }}
html {{ scroll-behavior: auto; }}
</style>

<script>document.documentElement.classList.add('intro');</script>

<a class="skip-link" href="#main">Skip to content</a>

{nav}

<main id="main">
{chr(10).join(routes_html)}
</main>

{footer}

{lightbox}

<script>{JS}</script>
"""
    open(OUT, "w", encoding="utf-8").write(doc)
    print(f"\nbundle: {OUT}  {os.path.getsize(OUT)/1024/1024:.2f} MB")


if __name__ == "__main__":
    print("bundling WUJOE site:")
    build()
