# Sources of Rajiv Malhotra's books (if-books-backup)

Every book gets one standalone page that lists its endnotes exactly as printed, in book order, under chapter headings. Each entry has a **Saved PDF** button (our preserved copy) and an **Original link** button. Pages are meant to be linked from, and later embedded in, the matching book page on https://rajivmalhotra.com/books/.

- Site: https://ankita-jagdeep123.github.io/if-books-backup/
- AIFP: https://ankita-jagdeep123.github.io/if-books-backup/books/AIFP/ (short link: `/aifp/`)

The pages are plain static HTML with inline CSS and no outside dependencies. Each book page loads `sources.json` and carries an embedded copy, so it also works when opened from disk.

## Layout
```
index.html                 list of books (generated, in rajivmalhotra.com/books/ order)
books/order.json           that order; add "code" to a book once its page exists
books/AIFP/book.json       title, author, chapter titles and endnote ranges
books/AIFP/AIFP_sources.csv  master spreadsheet (read only by the build)
books/AIFP/Saved PDFs/     saved copies, named as in the "Backup file" column
books/AIFP/index.html      generated book page
books/AIFP/sources.json    generated data
templates/                 page templates (edit these for design changes)
build_library.py           builds everything above
```

## What each entry shows
- The endnote number and the "Note / citation text" column, as printed.
- **Saved PDF**: the "OneDrive link" if filled in (view links only; edit links are ignored). Otherwise the file named in "Backup file", if it is in `Saved PDFs/`.
- **Original link**: each URL in the "URL" column.
- Status "Cannot obtain": the note "Original no longer available", with no PDF button.
- Bibliography rows not cited in any endnote are listed at the end.

## Adding a new book
1. Create `books/<CODE>/` (for example `books/BI/`).
2. Add `book.json` with the title, author, and a `chapters` list (`title`, `from`, `to` endnote numbers). Copy AIFP's as a model.
3. Add the spreadsheet as `<CODE>_sources.csv` (same columns as AIFP) and the PDFs in `Saved PDFs/`.
4. In `books/order.json`, add `"code": "<CODE>"` to that book's line.
5. Commit and push. The GitHub Action runs `build_library.py` and the page appears at `/books/<CODE>/`. To preview, run `python3 build_library.py` locally and open the file.

## GitHub Pages
Settings → Pages → Deploy from branch `main`, folder `/ (root)`.

## OneDrive
On hold until we confirm that view links open without a sign-in. Until then, Saved PDF uses the copies in the repo.

Never commit API keys, passwords or edit links.
