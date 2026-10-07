# Book Sources Archive (if-books-backup)

A legal bibliography backup for Rajiv Malhotra's books (Infinity Foundation). For each book the site lists **every source the book cites**: endnotes and bibliography. It shows which endnotes cite each source and links to our own saved copy, so a lawyer, researcher, or journalist can check the sources even if the original pages disappear.

Live site: https://ankita-jagdeep123.github.io/if-books-backup/

It is a plain static site with no build tool: `index.html` + `library.json`. A copy of the data is embedded in `index.html`, so the site also works when opened straight from disk (`file://`). It can be copied unchanged to the Infinity Foundation website.

## Layout
```
index.html            the whole site (home page + one page per book)
library.json          generated, do not edit by hand
build_library.py      reads every books/<CODE>/<CODE>_sources.csv and writes library.json
books/
  AIFP/
    book.json         title, author, year
    AIFP_sources.csv  the master spreadsheet, exported as CSV
    Saved PDFs/       saved copies (file names = "Backup file" column)
.github/workflows/build-library.yml   rebuilds library.json when a CSV changes
```

## How the spreadsheet is read
- Footnotes citing the same source (same **Source ID**, or the same **URL**) are shown once, with all their endnote numbers.
- **Category** gives the heading: `URL` → Web pages, `Book/Print` → Books and reports, `Social post` → Social posts, `Unlinked note` → Notes not yet linked to a source.
- **Status** gives the chip: `Downloaded` / `On OneDrive` / `Screenshots saved` → Saved copy. `Cannot obtain` → No longer online, with no PDF button. Anything else → To do.
- **"Open saved copy (PDF)"** uses the `OneDrive link` if filled in. Otherwise it uses `books/<CODE>/Saved PDFs/<Backup file>`, but only if that file is actually in the repo. Links that look like OneDrive *edit* links are ignored. Use view-only links.
- The `Remarks` column is internal and is not shown on the site.

## Adding a new book
1. Make a folder `books/<CODE>/` (e.g. `books/BI/`).
2. Add `book.json`: `{"code": "BI", "title": "Breaking India", "author": "Rajiv Malhotra", "year": 2011}`.
3. Export the master spreadsheet as `<CODE>_sources.csv`, with the same columns as AIFP, and put it in the folder.
4. Put saved PDFs in `books/<CODE>/Saved PDFs/`, named as in the "Backup file" column.
5. Commit and push. The GitHub Action rebuilds `library.json` and the site updates in a minute or two. To preview locally, run `python3 build_library.py` and open `index.html`.

## GitHub Pages setup
Settings → Pages → Source: *Deploy from a branch* → Branch `main`, folder `/ (root)` → Save. The site appears at `https://<user>.github.io/if-books-backup/`.

## OneDrive (on hold)
PDF buttons currently use the copies stored in this repo. Once we confirm that OneDrive view links open without a Microsoft sign-in, paste them into the `OneDrive link` column and they will be used automatically.

## Rules
Never commit API keys, passwords, or OneDrive edit links.
