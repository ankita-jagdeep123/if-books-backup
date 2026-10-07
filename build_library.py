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
EDIT = re.compile(r"[?&](e=|action=edit)|/edit\b", re.I)


def get(r, name):
    for k, v in r.items():
        if k and k.strip().lower().startswith(name.lower()):
            return (v or "").strip()
    return ""


def urls(s):
    return [u.strip() for u in re.split(r"\s+\|\s+|\s*\n\s*", s or "") if u.strip().startswith("http")]


def pdf_link(r, folder):
    od = get(r, "OneDrive link")
    if od and not EDIT.search(od):
        return od
    bf = get(r, "Backup file")
    if bf and os.path.exists(os.path.join(folder, "Saved PDFs", bf)):
        return "Saved PDFs/" + bf
    return ""


def entry(r, folder, label):
    gone = get(r, "Status").lower() in GONE
    return {"n": label, "text": get(r, "Note / citation text") or get(r, "Source (full citation)"),
            "pdf": "" if gone else pdf_link(r, folder), "urls": urls(get(r, "URL")), "gone": gone}


def build(folder):
    meta = json.load(open(os.path.join(folder, "book.json"), encoding="utf-8"))
    rows = []
    for c in sorted(glob.glob(os.path.join(folder, "*_sources.csv"))):
        with open(c, encoding="utf-8-sig", newline="") as f:
            rows += list(csv.DictReader(f))
    notes = {}
    bib = []
    for r in rows:
        num = get(r, "Note #")
        if get(r, "Row type").lower().startswith("note") and num.isdigit():
            notes[int(num)] = entry(r, folder, int(num))
        elif get(r, "Source (full citation)"):
            e = entry(r, folder, "")
            e["text"] = get(r, "Source (full citation)")
            bib.append(e)
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
    n = len(notes)
    print(f"{meta['code']}: {n} endnotes, {len(bib)} bibliography-only, "
          f"{sum(1 for c in chapters for e in c['entries'] if e['pdf'])} with saved PDF, "
          f"{sum(1 for c in chapters for e in c['entries'] if e['urls'])} with original link")
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
