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
from urllib.parse import urlsplit

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


# Optional per-book settings in book.json (all off unless set; AIFP sets none of them):
#   "chaptersFromCsv": true     endnote numbers restart in each chapter; chapters come from the CSV's
#                               "Chapter" (number, gives the order) and "Chapter name" columns
#   "requireBackupFile": true   Open PDF only when BOTH "Backup file" and "OneDrive link" are filled
#   "commentLabel": "..."       wording for Category "Unlinked note" rows (default: Author's comment...)
#   "commentStat": "..."        wording of that card in the stats row
#   "deadLinkNote": true        rows whose original address is dead (see dead()) get the sentence
#                               DEAD_TEXT above their buttons, when a Wayback copy or saved file exists
#   "fileLabels": true          a saved file that is not a .pdf gets "Download <EXT>" instead of "Open PDF"
# Button wording by the saved file's type, in every book (other types: "Open PDF", or with
# "fileLabels" "Download <EXT>").
FILE_LABELS = {"TXT": "Open text"}
# Several saved files for one source: put all their links in "OneDrive link", separated by " | "
# (space, pipe, space), in order. The page then shows "Part 1", "Part 2", ... buttons (styled like
# Open PDF) instead of a single button; the source counts once as saved.
DEAD_TEXT = "Original link is dead, but we found the following equivalent to serve the purpose."
DEAD_FAIL = re.compile(r"download failed - live page: ([^|]*)", re.I)


def dead(r):
    """The CSV marker for a dead original address, from the "Remarks" column:
    - "... from Wayback snapshot ..." (the saved copy had to come from the Wayback Machine), or
    - "download failed - live page: <reason>" where the reason is not HTTP 401/403 (those mean the
      page exists but refused the robot), unless a later attempt says "... from live page ..."."""
    rem = get(r, "Remarks")
    if re.search(r"from wayback snapshot", rem, re.I):
        return True
    if re.search(r"from live page", rem, re.I):
        return False
    return any(not re.search(r"\b40[13]\b", m.group(1)) for m in DEAD_FAIL.finditer(rem))


def address(r, opt=None):
    """One address block = one CSV row: its own PDF, original link(s) and wayback link(s)."""
    opt = opt or {}
    gone = get(r, "Status").lower() in GONE
    us, wb = urls(get(r, "URL")), urls(get(r, "Wayback link"))
    pdf = "" if gone else onedrive(r)
    if pdf and opt.get("requireBackupFile") and not get(r, "Backup file"):
        print(f"WARNING {get(r, 'ID')}: OneDrive link but no Backup file; Open PDF not shown", file=sys.stderr)
        pdf = ""
    comment = (not gone and not pdf and not us and not wb and not get(r, "Backup file")
               and get(r, "Category").lower() == "unlinked note")
    a = {"pdf": pdf, "gone": gone, "comment": comment,
         "links": [{"url": u, "wayback": wb[i] if i < len(wb) else ""} for i, u in enumerate(us)]
                  or ([{"url": "", "wayback": w} for w in wb])}
    if opt.get("deadLinkNote") and not gone and (wb or pdf) and dead(r):
        a["dead"] = True
    ext = os.path.splitext(get(r, "Backup file"))[1].lstrip(".").upper()
    if ext in FILE_LABELS and pdf:
        a["label"] = FILE_LABELS[ext]
    elif opt.get("fileLabels") and pdf and ext and ext != "PDF":
        a["label"] = "Download " + ext
    parts = urls(pdf)
    if len(parts) > 1:
        # several saved files in one "OneDrive link" cell ("link1 | link2"): Part 1, Part 2, ...
        a["pdf"] = parts[0]
        a["files"] = [{"url": u, "label": f"Part {i + 1}"} for i, u in enumerate(parts)]
    return a


# Stats row: every numbered endnote (Row type "Note") counted once, by its Category.
# The parts must add up to the total number of endnotes, or the build fails.
STAT_PARTS = [("web", "url"), ("social", "social post"), ("books", "book/print"), ("comments", "unlinked note")]


def stats(rows, endnotes):
    """Static counts for the stats row at the top of the page, all taken from the CSV.
    endnotes : numbered endnotes (Row type exactly "Note"; "Note (extra address)" and
               "Bibliography only" rows are not counted)
    web      : endnotes with Category "URL"          (cite a web page)
    social   : endnotes with Category "Social post"  (cite a social media post)
    books    : endnotes with Category "Book/Print"   (cite a book, report, article or other printed work)
    comments : endnotes with Category "Unlinked note" (the author's own comment, no source)
    web + social + books + comments == endnotes is asserted."""
    cats = [get(r, "Category").lower() for r in rows if get(r, "Row type").lower() == "note"]
    out = {"endnotes": len(cats)}
    for key, cat in STAT_PARTS:
        out[key] = sum(1 for c in cats if c == cat)
    other = sorted({c for c in cats if c not in {cat for _, cat in STAT_PARTS}})
    parts = sum(out[k] for k, _ in STAT_PARTS)
    if other or parts != out["endnotes"] or out["endnotes"] != endnotes:
        sys.exit(f"STATS DO NOT ADD UP: {out} (parts {parts}, endnotes on page {endnotes}); "
                 f"unknown Category on Note rows: {other or 'none'}")
    return out


def build(folder):
    meta = json.load(open(os.path.join(folder, "book.json"), encoding="utf-8"))
    rows = []
    for c in sorted(glob.glob(os.path.join(folder, "*_sources.csv"))):
        with open(c, encoding="utf-8-sig", newline="") as f:
            rows += list(csv.DictReader(f))
    percsv = bool(meta.get("chaptersFromCsv"))
    notes, bib, extras, pending, chnames = {}, [], 0, [], {}
    for r in rows:
        if not any((v or "").strip() for v in r.values() if isinstance(v, str)):
            continue  # blank row
        rt = get(r, "Row type").lower()
        num = get(r, "Note #")
        if not num.isdigit():
            m = re.search(r"_N(\d+)", get(r, "ID"))
            num = m.group(1) if m else num
        if rt.startswith("note") and num.isdigit():
            n = key = int(num)
            if percsv:
                ch = get(r, "Chapter")
                if not ch.isdigit():
                    sys.exit(f"{get(r, 'ID')}: Chapter must be a number when chaptersFromCsv is set")
                key = (int(ch), n)
                chnames.setdefault(int(ch), get(r, "Chapter name") or f"Chapter {ch}")
            if "extra" in rt:
                extras += 1
                pending.append((key, n, r))
                continue
            if key in notes:
                print(f"WARNING {get(r, 'ID')}: duplicate note {key}; the later row wins", file=sys.stderr)
            notes[key] = {"n": n, "text": get(r, "Note / citation text") or get(r, "Source (full citation)"),
                          "addr": [address(r, meta)]}
        elif get(r, "Source (full citation)"):
            bib.append({"n": "", "text": get(r, "Source (full citation)"), "addr": [address(r, meta)]})
    for key, n, r in pending:
        if key in notes:
            notes[key]["addr"].append(address(r, meta))
        else:
            print(f"WARNING {get(r, 'ID')}: extra address for note {key} has no parent note row", file=sys.stderr)
            notes[key] = {"n": n, "text": get(r, "Note / citation text"), "addr": [address(r, meta)]}
    chapters, used = [], set()
    if percsv:
        for c in sorted(chnames):
            chapters.append({"title": chnames[c], "entries": [notes[k] for k in sorted(notes) if k[0] == c]})
        used = set(notes)
    for ch in [] if percsv else meta.get("chapters", []):
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
    nl = list(notes.values())
    comments = sum(1 for e in nl if all(a["comment"] for a in e["addr"]))
    saved = sum(1 for e in nl if any(a["pdf"] for a in e["addr"]))
    data = {"code": meta["code"], "title": meta["title"], "author": meta.get("author", ""),
            "stats": stats(rows, len(nl)),
            "progress": {"endnotes": len(nl), "cite": len(nl) - comments, "saved": saved, "comments": comments},
            "chapters": chapters}
    with open(os.path.join(folder, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    tpl = open(os.path.join(ROOT, "templates", "book.html"), encoding="utf-8").read()
    emb = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    A = [a for c in chapters for e in c["entries"] for a in e["addr"]]
    # The button line only switches to the label/parts form when this book needs it, so a book
    # without such rows gets exactly the same page as before.
    labelled = meta.get("fileLabels") or any(a.get("label") for a in A)
    if any(a.get("files") for a in A):
        btn = ("(a.files || [{ url: a.pdf, label: a.label || \"Open PDF\" }]).forEach(function (f) { "
               "h.push('<a class=\"btn pdf\" href=\"' + esc(f.url) + '\" target=\"_blank\" rel=\"noopener\">' + esc(f.label) + '</a>'); });")
    else:
        btn = ("h.push('<a class=\"btn pdf\" href=\"' + esc(a.pdf) + '\" target=\"_blank\" rel=\"noopener\">"
               + ("' + esc(a.label || \"Open PDF\") + '" if labelled else "Open PDF") + "</a>');")
    page = (tpl.replace("{{TITLE}}", html.escape(meta["title"]))
               .replace("{{AUTHOR}}", html.escape(meta.get("author", "")))
               .replace("{{COMMENT_LABEL}}", html.escape(meta.get("commentLabel", "Author\\u2019s comment, no source to save")))
               .replace("{{COMMENT_STAT}}", html.escape(meta.get("commentStat", "Author\\u2019s comment")))
               .replace("{{PDF_BTN}}", btn)
               .replace("{{DEAD_JS}}", "\n    if (a.dead) h.push('<span class=\"dead\">" + DEAD_TEXT + "</span>');"
                        if meta.get("deadLinkNote") else "")
               .replace("{{EXTRA_CSS}}", "\n  .dead { flex-basis: 100%; font-size: .78rem; color: var(--soft); font-style: italic; }"
                        if meta.get("deadLinkNote") else "")
               .replace("/*DATA*/null", emb))
    open(os.path.join(folder, "index.html"), "w", encoding="utf-8").write(page)
    other = {}
    for a in A:
        if a["pdf"] and (a.get("label") or a.get("files")):
            k = (a.get("label") or "Open PDF") + (f" in {len(a['files'])} parts" if a.get("files") else "")
            other[k] = other.get(k, 0) + 1
    print(f"{meta['code']}: {len(notes)} endnotes, {len(bib)} bibliography-only, {extras} extra-address rows grouped; "
          f"buttons: Open PDF {sum(1 for a in A if a['pdf'] and not a.get('label') and not a.get('files'))}, "
          f"other saved files {other or 0} ({sum(len(a.get('files', [])) or 1 for a in A if a['pdf'] and (a.get('label') or a.get('files')))} buttons), "
          f"PDF not saved yet {sum(1 for a in A if not a['pdf'] and not a['gone'] and not a['comment'])}, "
          f"Copy not available {sum(1 for a in A if a['gone'])}, Author's comment {sum(1 for a in A if a['comment'])}, "
          f"dead-link sentence {sum(1 for a in A if a.get('dead'))}; "
          f"progress: {saved} of {len(nl) - comments} source endnotes saved; stats: {data['stats']}")
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
