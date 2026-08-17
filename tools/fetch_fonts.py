#!/usr/bin/env python3
"""Download the site's webfonts and emit @font-face rules with the woff2 inlined.

The Artifact CSP blocks font CDNs, so a <link> to Google Fonts would silently
fall back to Times/system-ui in the shared bundle. Inlining keeps the page
looking like the real site on any machine.

Run this once; bundle.py reads the fonts.css it writes.
"""
import base64, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fonts.css")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
# only the weights styles.css actually uses
CSS_URL = ("https://fonts.googleapis.com/css2"
           "?family=Caveat:wght@500"
           "&family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500"
           "&family=Inter:wght@400;500;600"
           "&display=swap")
# English text plus the Greek deltas/alpha in the stablecoin paper.
# latin-ext would triple the payload for accents the site never uses.
KEEP = {"latin", "greek"}
NO_GREEK = {"Caveat"}          # one handwritten caption; latin is enough


def get(url, binary=False):
    r = subprocess.run(["curl", "-sS", "-m", "40", "-A", UA, url],
                       capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode()


def main():
    css = get(CSS_URL)
    blocks = re.findall(r'/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})', css, re.S)
    out, total = [], 0
    for subset, block in blocks:
        if subset not in KEEP:
            continue
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        if subset == "greek" and fam in NO_GREEK:
            continue
        m = re.search(r'url\((https://fonts\.gstatic\.com[^)]+\.woff2)\)', block)
        if not m:
            continue
        data = get(m.group(1), binary=True)
        total += len(data)
        uri = "data:font/woff2;base64," + base64.b64encode(data).decode()
        wgt = re.search(r'font-weight:\s*(\d+)', block).group(1)
        sty = re.search(r'font-style:\s*(\w+)', block).group(1)
        print(f"  {fam:14} {sty:7} {wgt}  {subset:6} {len(data)/1024:6.1f} KB")
        out.append(block.replace(m.group(0), f"url({uri})"))

    open(OUT, "w", encoding="utf-8").write("\n".join(out))
    print(f"\n{len(out)} faces, {total/1024:.0f} KB raw -> {OUT}")


if __name__ == "__main__":
    main()
