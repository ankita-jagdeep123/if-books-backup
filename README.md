# Sources of Rajiv Malhotra's books (if-books-backup)

Every book gets one standalone page that lists its endnotes exactly as printed, in book order, under chapter headings. Each entry has an **Open PDF** button (our preserved copy) and an **Original link** button. Pages are meant to be linked from, and later embedded in, the matching book page on https://rajivmalhotra.com/books/.

- Site: https://ankita-jagdeep123.github.io/if-books-backup/
- AIFP: https://ankita-jagdeep123.github.io/if-books-backup/books/AIFP/ (short link: `/aifp/`)

The pages are plain static HTML with inline CSS and no outside dependencies. Each book page loads `sources.json` and carries an embedded copy, so it also works when opened from disk.

## Layout
```
index.html                 list of books (generated, in rajivmalhotra.com/books/ order)
books/order.json           that order; add "code" to a book once its page exists
books/AIFP/book.json       title, author, chapter titles and endnote ranges
books/AIFP/AIFP_sources.csv  master spreadsheet (read only by the build)
books/AIFP/index.html      generated book page
books/AIFP/sources.json    generated data
templates/                 page templates (edit these for design changes)
build_library.py           builds everything above
```

## Updating a book after each batch (one step)
Replace `books/AIFP/AIFP_sources.csv` with the new export, keeping the same name and path, and commit it. On GitHub you can use **Add file → Upload files** in `books/AIFP/` and drop the CSV there. The **Rebuild library.json** Action then runs on its own, rebuilds the page and data, and commits them. The live page updates a minute or two later. Nothing else needs editing.
The build doesn't care about column order, extra columns, or blank rows, because columns are matched by header name.
If you work locally instead: copy the new CSV over `books/AIFP/AIFP_sources.csv`, then `git add books/AIFP/AIFP_sources.csv && git commit -m "AIFP: new CSV" && git push`. The Action does the rest.

## What each entry shows
- The endnote number and the "Note / citation text" column, as printed.
- **Open PDF** opens the row's "OneDrive link" in a new tab. Use **view-only** share links. A link that looks like an edit link (`action=edit`, `/edit`, `:w:/r/`…) is treated as missing, and the build logs a WARNING. The `?e=…` at the end of normal 1drv.ms share links is fine.
- With no OneDrive link, a greyed **PDF not saved yet** is shown. With Status "Cannot obtain", a greyed **Copy not available** and "Original no longer available" are shown.
- **Original link** is shown for each URL, plus a small **Wayback** link when the "Wayback link" column is filled in.
- **Note (extra address)** rows are listed under their parent endnote, by Note #, or by the number in the ID such as `AIFP_N038…`. Each gets its own Open PDF / Original link / Wayback buttons.
- Bibliography rows not cited in any endnote are listed at the end.

## Adding a new book
1. Create `books/<CODE>/` (for example `books/BI/`).
2. Add `book.json` with the title, author, and a `chapters` list (`title`, `from`, `to` endnote numbers). Copy AIFP's as a model.
3. Add the spreadsheet as `<CODE>_sources.csv` (same columns as AIFP) and paste OneDrive view links in the "OneDrive link" column.
4. In `books/order.json`, add `"code": "<CODE>"` to that book's line.
5. Commit and push. The GitHub Action runs `build_library.py` and the page appears at `/books/<CODE>/`. To preview, run `python3 build_library.py` locally and open the file.

## GitHub Pages
Settings → Pages → Deploy from branch `main`, folder `/ (root)`.

## OneDrive
PDF buttons link only to OneDrive. Until a row has its OneDrive link, it shows "PDF not saved yet".

Never commit API keys, passwords or edit links.
