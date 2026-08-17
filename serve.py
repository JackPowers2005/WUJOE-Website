"""Local server for the WUJOE site.

Two things this does that `python3 -m http.server` does not:

1. Sends `Cache-Control: no-store` on every response. Plain http.server sends
   only Last-Modified, so Safari applies "heuristic freshness" and will reuse a
   stored page without ever asking the server whether it changed.

2. Stamps every internal page link with a hash of the file it points at, at
   response time. Point 1 stops NEW stale copies being stored, but it cannot
   invalidate one a browser already holds -- nothing sent from here can reach a
   response the browser decides not to re-request. Serving links as
   `articles.html?b=<hash>` sidesteps that entirely: the URL changes whenever
   the target file changes, so a stale entry can never be matched in the first
   place.

The stamping happens in-flight only. Files on disk keep clean hrefs, so the
bundled/published artifact is unaffected.

Symptoms this was written to kill: a swapped headshot that kept rendering the
previous photo, and a withdrawn article that kept appearing on the homepage.
"""
import functools
import hashlib
import io
import os
import posixpath
import re
import sys
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


def _default_site():
    """Find the site root, so this works from either layout: sitting beside a
    wujoe-website/ folder, or sitting at the root of a checkout next to
    index.html."""
    here = os.path.dirname(os.path.abspath(__file__))
    sib = os.path.join(here, "wujoe-website")
    if os.path.isfile(os.path.join(sib, "index.html")):
        return sib
    if os.path.isfile(os.path.join(here, "index.html")):
        return here
    raise SystemExit("serve.py: could not find the site (no index.html found)")


SITE = sys.argv[2] if len(sys.argv) > 2 else _default_site()

HREF = re.compile(rb'href="([^"]+\.html)((?:#[^"]*)?)"')


def _hash(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()[:8]


class FreshHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _stamp(self, body, page_dir):
        def rep(m):
            target, frag = m.group(1).decode(), m.group(2).decode()
            if target.startswith(("http", "mailto:", "//", "data:")):
                return m.group(0)
            clean = target.split("?", 1)[0]
            path = os.path.normpath(os.path.join(page_dir, clean))
            if not (path.startswith(SITE) and os.path.isfile(path)):
                return m.group(0)
            return ('href="%s?b=%s%s"' % (clean, _hash(path), frag)).encode()
        return HREF.sub(rep, body)

    def send_head(self):
        # a conditional request could still be answered 304, re-introducing the
        # stale render, so drop the validators before the base class sees them
        for h in ("If-Modified-Since", "If-None-Match"):
            if h in self.headers:
                del self.headers[h]

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith("/"):
                return super().send_head()      # let it issue the redirect
            for index in ("index.html", "index.htm"):
                cand = os.path.join(path, index)
                if os.path.isfile(cand):
                    path = cand
                    break

        if not (path.endswith(".html") and os.path.isfile(path)):
            return super().send_head()

        with open(path, "rb") as fh:
            body = self._stamp(fh.read(), os.path.dirname(path))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return io.BytesIO(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    SITE = os.path.abspath(SITE)
    handler = functools.partial(FreshHandler, directory=SITE)
    print("Serving %s on http://localhost:%d" % (SITE, PORT))
    print("no-store + versioned page links: what you see is always what is on disk")
    ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
