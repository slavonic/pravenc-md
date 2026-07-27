# pravenc-md

*Православная энциклопедия* (*Orthodox Encyclopedia*) articles in Markdown format.

This repository contains the articles published in the [electronic version of the Orthodox Encyclopedia](https://pravenc.ru/) converted to Markdown, together with the scripts used to produce them. It is intended for purposes of search, querying, and machine learning.

## Repository layout

| Path | Contents |
| --- | --- |
| [articles/](articles/) | The converted articles, one Markdown file per article. |
| [scripts/](scripts/) | All Python scripts (scraping pipeline and Church Slavonic / Syriac utilities). |
| [data/](data/) | The character mapping used by the converters, plus a stylesheet and example page. |
| [data/char-maps/](data/char-maps/) | Working files for building character mappings: extracted code lists and the HTML mapping sheets. |

## Article format

Each file is Markdown with YAML front matter:

```yaml
---
article_title: АВКСЕНТИЙ
author: П. Б. Михайлов
volume: '1'
page_numbers: '143'
source_url: https://pravenc.ru/text/62806.html
downloaded_at: '2026-07-27T17:51:24Z'
---
```

The body preserves the article's headings (Источники, Литература, and so on), cross-references as links to `pravenc.ru`, and footnote-style references. Church Slavonic passages appear as `<span class="cu">…</span>` (see [Church Slavonic text](#church-slavonic-text) below).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The scripts resolve their input and output paths relative to the repository, so they can be run from any working directory.

## Workflow

Refreshing the corpus is a two-step pipeline. Run step 1, then step 2.

### 1. Collect the article URLs

```bash
python scripts/extract_urls.py
```

This walks the encyclopedia's [article listing](https://pravenc.ru/list.html), page by page, and writes every article URL it finds to `article_urls.txt`. The number of listing pages is read from the site's own pagination block on each run, so it keeps up automatically as new articles are published; pass `--start-page` / `--end-page` to override the range, or `--output` to write elsewhere.

### 2. Download and convert the articles

```bash
python scripts/batch_scrape.py
```

This reads `article_urls.txt` and, for each URL, downloads the article and converts it to Markdown in `articles/`. **If a Markdown file for that article already exists it is skipped**, so re-running only fetches articles that are new since the last run. Options: `--out-dir` for a different destination and `--delay` to change the pause between requests (0.5 s by default — please keep a courteous delay).

To fetch a single article instead of the whole list:

```bash
python scripts/scrape_pravenc.py https://pravenc.ru/text/62806.html
```

## Church Slavonic text

The encyclopedia does not publish Church Slavonic as text — it renders each passage as an image under `https://pravenc.ru/char/…`, whose URL encodes the characters as a sequence of hex chunks such as `x010`. The utilities below turn those image references back into Unicode.

The mapping itself lives in [data/cu.json](data/cu.json), which maps each hex chunk to its Unicode equivalent (`"x010": "ⷣ҇"`). It was assembled by hand, using generated HTML sheets that show each code next to its image.

### Applying the mapping

- **[scripts/convert_church_slavonic_to_unicode.py](scripts/convert_church_slavonic_to_unicode.py)** — the main converter. Rewrites Church Slavonic image references in `articles/` into Unicode wrapped in `<span class="cu">`, using `data/cu.json`. It is interactive and offers a dry run first. Any chunk missing from the mapping is left visible as `[xNN]` so gaps are easy to find.
- **[scripts/convert_div_to_span.py](scripts/convert_div_to_span.py)** — a one-off fix-up that rewrites `<div class="cu">` to `<span class="cu">`, so the passages sit inline in the surrounding paragraph.

### Extending the mapping

Run these only when new, unmapped characters appear:

1. **Extract the codes** actually used in the articles:
   - `scripts/extract_all_church_slavonic_codes.py` — extracts codes from Church Slavonic images, covering both the `char/26526` and `char/26528` URL forms and writing a separate list for each.
   - `scripts/extract_syriac_codes.py` — the equivalent for Syriac, which is stored the same way under `char/26094`.
2. **Build a mapping sheet** — an HTML table showing every code beside its rendered image, for filling in by hand:
   - `scripts/create_complete_church_slavonic_mapping.py`
   - `scripts/create_syriac_mapping.py`
3. **Transfer** the identified characters into `data/cu.json` and re-run the converter.

All of these read from and write to [data/char-maps/](data/char-maps/).

### Displaying the text

Church Slavonic needs a font with the required combining marks, such as [Ponomar](https://sci.ponomar.net/fonts.html). [data/church_slavonic.css](data/church_slavonic.css) styles the `.cu` spans, and [data/church_slavonic_example.html](data/church_slavonic_example.html) is a small page demonstrating the result.

## License

See [LICENSE](LICENSE). The underlying articles are © Церковно-научный центр «Православная Энциклопедия».
