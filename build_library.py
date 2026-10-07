#!/usr/bin/env python3
"""Build library.json from every books/<CODE>/<CODE>_sources.csv.

Run:  python3 build_library.py
- Reads each *_sources.csv (plus optional book.json with the title).
- Merges footnotes that cite the same source (same Source ID, else same URL).
- Groups sources by book, then by source type.
- Writes library.json and refreshes the offline copy embedded in index.html.
No network access, no API keys.
"""
import csv, glob, json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
TYPES = [  # (id, heading, CSV categories)
    ("web", "Web pages", {"url", "web", "web page"}),
    ("book", "Books and reports", {"book/print", "book", "report", "print"}),
    ("social", "Social posts", {"social post", "social"}),
    ("unlinked", "Notes not yet linked to a source", {"unlinked note", "unlinked", ""}),
]
SAVED = {"downloaded", "on onedrive", "screenshots saved"}
GONE = {"cannot obtain"}
EDIT_LINK = re.compile(r"(\?|&)(e=|edit|action=edit)|/edit\b|:w:/|:x:/|:b:/.*e=", re.I)


def col(r, *names):
    for n in names:
        for k in r:
            if k and k.strip().lower().startswith(n.lower()):
                v = (r[k] or "").strip()
                if v:
                    return v
    return ""


def split_urls(s):
    return [u.strip() for u in re.split(r"\s+\|\s+|\s*\n\s*", s or "") if u.strip().startswith("http")]


def norm_url(u):
    u = u.strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    return u.rstrip("/")


def type_of(cat):
    c = (cat or "").strip().lower()
    for tid, _, cats in TYPES:
        if c in cats:
            return tid
    return "book"


def status_group(st):
    s = (st or "").strip().lower()
    if s in GONE:
        return "gone"
    if s in SAVED:
        return "saved"
    return "todo"


def safe_link(u):
    """Only keep view links; drop anything that looks like an edit link."""
    if not u:
        return ""
    if EDIT_LINK.search(u):
        print(f"  ! skipped a link that looks like an edit link: {u[:60]}...", file=sys.stderr)
        return ""
    return u


def build_book(folder):
    code = os.path.basename(folder)
    meta = {"code": code, "title": code}
    bj = os.path.join(folder, "book.json")
    if os.path.exists(bj):
        meta.update(json.load(open(bj, encoding="utf-8")))
    csvs = sorted(glob.glob(os.path.join(folder, "*_sources.csv")))
    rows = []
    for c in csvs:
        with open(c, encoding="utf-8-sig", newline="") as f:
            rows += list(csv.DictReader(f))
    sources, key_of = [], {}
    for order, r in enumerate(rows):
        rid = col(r, "ID")
        if not rid:
            continue
        sid = col(r, "Source ID")
        urls = split_urls(col(r, "URL"))
        keys = ([f"sid:{sid}"] if sid else []) + [f"url:{norm_url(u)}" for u in urls]
        s = next((key_of[k] for k in keys if k in key_of), None)
        if s is None:
            s = {"id": sid or rid, "rows": [], "notes": [], "type": None, "citation": "",
                 "urls": [], "wayback": [], "googleBooks": "", "pdf": "", "status": "",
                 "order": order}
            sources.append(s)
        for k in keys:
            key_of[k] = s
        s["rows"].append(rid)
        is_note = col(r, "Row type").lower().startswith("note")
        num = col(r, "Note #")
        if is_note and num:
            n = {"n": int(num) if num.isdigit() else num}
            page = col(r, "Cited page")
            if page:
                n["page"] = page
            ch = col(r, "Chapter name") or col(r, "Chapter")
            if ch:
                n["chapter"] = ch
            if not any(x["n"] == n["n"] for x in s["notes"]):
                s["notes"].append(n)
        full = col(r, "Source (full citation)", "Source")
        if full and not s["citation"]:
            s["citation"] = full
        if not s["citation"] and not sid:
            s["citation"] = col(r, "Note / citation text")
        t = type_of(col(r, "Category"))
        if s["type"] is None or (s["type"] == "unlinked" and t != "unlinked"):
            s["type"] = t
        for u in urls:
            if u not in s["urls"]:
                s["urls"].append(u)
        for u in split_urls(col(r, "Wayback link")):
            if u not in s["wayback"]:
                s["wayback"].append(u)
        s["googleBooks"] = s["googleBooks"] or col(r, "Google Books link")
        st = col(r, "Status")
        # strongest status wins: saved > todo; "Cannot obtain" only if nothing saved
        if status_group(st) == "saved" or not s["status"]:
            s["status"] = st or "To do"
        od = safe_link(col(r, "OneDrive link"))
        bf = col(r, "Backup file")
        if od:
            s["pdf"] = od
        elif bf and not s["pdf"]:
            rel = os.path.join("books", code, "Saved PDFs", bf)
            if os.path.exists(os.path.join(ROOT, rel)):
                s["pdf"] = rel.replace(os.sep, "/")
            else:
                s.setdefault("pendingFile", bf)
    out_sources = []
    for s in sources:
        s["notes"].sort(key=lambda x: (isinstance(x["n"], str), x["n"]))
        g = status_group(s["status"])
        if g == "gone":
            s["pdf"] = ""
        if not s["citation"]:
            s["citation"] = "(citation text missing in spreadsheet)"
        s["statusGroup"] = g
        s["firstNote"] = s["notes"][0]["n"] if s["notes"] and isinstance(s["notes"][0]["n"], int) else 10**6 + s["order"]
        s.pop("order")
        s.pop("rows")
        out_sources.append(s)
    out_sources.sort(key=lambda s: s["firstNote"])
    groups = []
    for tid, heading, _ in TYPES:
        items = [s for s in out_sources if s["type"] == tid]
        if items:
            groups.append({"type": tid, "heading": heading, "sources": items})
    counts = {
        "sources": len(out_sources),
        "endnotes": sum(len(s["notes"]) for s in out_sources),
        "savedCopies": sum(1 for s in out_sources if s["pdf"]),
        "saved": sum(1 for s in out_sources if s["statusGroup"] == "saved"),
        "todo": sum(1 for s in out_sources if s["statusGroup"] == "todo"),
        "gone": sum(1 for s in out_sources if s["statusGroup"] == "gone"),
        "byType": {g["type"]: len(g["sources"]) for g in groups},
    }
    meta.update({"counts": counts, "groups": groups})
    return meta


def main():
    books = [build_book(d) for d in sorted(glob.glob(os.path.join(ROOT, "books", "*")))
             if os.path.isdir(d) and glob.glob(os.path.join(d, "*_sources.csv"))]
    lib = {"meta": {"title": "Infinity Foundation: Book Sources Archive",
                    "updated": datetime.date.today().isoformat()},
           "books": books}
    with open(os.path.join(ROOT, "library.json"), "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=1)
    idx = os.path.join(ROOT, "index.html")
    if os.path.exists(idx):
        html = open(idx, encoding="utf-8").read()
        emb = json.dumps(lib, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        html = re.sub(r"(/\*FALLBACK_START\*/).*?(/\*FALLBACK_END\*/)",
                      lambda m: m.group(1) + emb + m.group(2), html, flags=re.S)
        open(idx, "w", encoding="utf-8").write(html)
    for b in books:
        c = b["counts"]
        print(f"{b['code']}: {c['sources']} sources, {c['endnotes']} endnotes, "
              f"{c['savedCopies']} saved copies online, {c['todo']} to do, {c['gone']} no longer online, by type {c['byType']}")


if __name__ == "__main__":
    main()
