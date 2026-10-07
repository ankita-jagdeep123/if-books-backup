#!/usr/bin/env python3
"""Build the static book pages from books/<CODE>/<CODE>_sources.csv.

Run:  python3 build_library.py
For each book folder with a *_sources.csv and a book.json it writes
  books/<CODE>/sources.json   the endnotes in book order, grouped by chapter
  books/<CODE>/index.html     the standalone page (template + embedded copy of the data)
and the root index.html (list of books in rajivmalhotra.com/books/ order).
The CSV is only read, never changed. No network access, no API keys.
"""
import csv, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GONE = {"cannot obtain"}
EDIT = re.compile(r"action=edit|[?&]edit=|/edit(?:[/?#]|$)|:[wxp]:/r/|editnew", re.I)
# Note: "?e=xxxx" on 1drv.ms share links is an access token, not an edit flag.


def get(r, name):
    """Column lookup by header name, ignoring case, spacing and column order."""
    want = re.sub(r"\W+", "", name.lower())
    keys = [k for k in r if isinstance(k, str)]
    exact = [k for k in keys if re.sub(r"\W+", "", k.lower()) == want]
    # Exact header match wins (so "Note #" never falls through to "Note / citation text").
    for k in exact or [k for k in keys if re.sub(r"\W+", "", k.lower()).startswith(want)]:
        v = r.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def urls(s):
    return [u.strip() for u in re.split(r"\s+\|\s+|\s*\n\s*", s or "") if u.strip().startswith("http")]


def onedrive(r):
    od = get(r, "OneDrive link")
    if not od:
        return ""
    if EDIT.search(od) or not od.startswith("https://"):
        print(f"WARNING {get(r, 'ID')}: OneDrive link looks like an edit link or is not https; treated as missing", file=sys.stderr)
        return ""
    return od


def address(r):
    """One address block = one CSV row: its own PDF, original link(s) and wayback link(s)."""
    gone = get(r, "Status").lower() in GONE
    us, wb = urls(get(r, "URL")), urls(get(r, "Wayback link"))
    return {"pdf": "" if gone else onedrive(r), "gone": gone,
            "links": [{"url": u, "wayback": wb[i] if i < len(wb) else ""} for i, u in enumerate(us)]
                     or ([{"url": "", "wayback": w} for w in wb])}


def build(folder):
    meta = json.load(open(os.path.join(folder, "book.json"), encoding="utf-8"))
    rows = []
    for c in sorted(glob.glob(os.path.join(folder, "*_sources.csv"))):
        with open(c, encoding="utf-8-sig", newline="") as f:
            rows += list(csv.DictReader(f))
    notes, bib, extras, pending = {}, [], 0, []
    for r in rows:
        if not any((v or "").strip() for v in r.values() if isinstance(v, str)):
            continue  # blank row
        rt = get(r, "Row type").lower()
        num = get(r, "Note #")
        if not num.isdigit():
            m = re.search(r"_N(\d+)", get(r, "ID"))
            num = m.group(1) if m else num
        if rt.startswith("note") and num.isdigit():
            n = int(num)
            if "extra" in rt:
                extras += 1
                pending.append((n, r))
                continue
            notes[n] = {"n": n, "text": get(r, "Note / citation text") or get(r, "Source (full citation)"),
                        "addr": [address(r)]}
        elif get(r, "Source (full citation)"):
            bib.append({"n": "", "text": get(r, "Source (full citation)"), "addr": [address(r)]})
    for n, r in pending:
        if n in notes:
            notes[n]["addr"].append(address(r))
        else:
            print(f"WARNING {get(r, 'ID')}: extra address for note {n} has no parent note row", file=sys.stderr)
            notes[n] = {"n": n, "text": get(r, "Note / citation text"), "addr": [address(r)]}
    chapters, used = [], set()
    for ch in meta.get("chapters", []):
        items = [notes[n] for n in range(ch["from"], ch["to"] + 1) if n in notes]
        used.update(range(ch["from"], ch["to"] + 1))
        if items:
            chapters.append({"title": ch["title"], "entries": items})
    rest = [notes[n] for n in sorted(notes) if n not in used]
    if rest:
        chapters.append({"title": "Other notes", "entries": rest})
    if bib:
        bib.sort(key=lambda e: e["text"].lower())
        chapters.append({"title": "Also in the bibliography (not cited in an endnote)", "entries": bib})
    data = {"code": meta["code"], "title": meta["title"], "author": meta.get("author", ""),
            "chapters": chapters}
    with open(os.path.join(folder, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    tpl = open(os.path.join(ROOT, "templates", "book.html"), encoding="utf-8").read()
    emb = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = (tpl.replace("{{TITLE}}", html.escape(meta["title"]))
               .replace("{{AUTHOR}}", html.escape(meta.get("author", "")))
               .replace("/*DATA*/null", emb))
    open(os.path.join(folder, "index.html"), "w", encoding="utf-8").write(page)
    A = [a for c in chapters for e in c["entries"] for a in e["addr"]]
    print(f"{meta['code']}: {len(notes)} endnotes, {len(bib)} bibliography-only, {extras} extra-address rows grouped; "
          f"buttons: Open PDF {sum(1 for a in A if a['pdf'])}, PDF not saved yet {sum(1 for a in A if not a['pdf'] and not a['gone'])}, "
          f"Copy not available {sum(1 for a in A if a['gone'])}")
    return meta


def main():
    books = {}
    for d in sorted(glob.glob(os.path.join(ROOT, "books", "*"))):
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "book.json")) and glob.glob(os.path.join(d, "*_sources.csv")):
            m = build(d)
            books[m["code"]] = m
    order = json.load(open(os.path.join(ROOT, "books", "order.json"), encoding="utf-8"))["order"]
    codes = [o["code"] for o in order if o.get("code") in books]
    codes += sorted(c for c in books if c not in codes)
    items = "\n".join(f'    <li><a href="books/{c}/">{html.escape(books[c]["title"])}</a></li>' for c in codes)
    tpl = open(os.path.join(ROOT, "templates", "home.html"), encoding="utf-8").read()
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(tpl.replace("{{BOOKS}}", items))


if __name__ == "__main__":
    main()
