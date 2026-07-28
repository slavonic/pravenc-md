#!/usr/bin/env python3
"""
Script to turn cross-references between articles into local Markdown links.

Articles link to each other by title, e.g. https://pravenc.ru/text/Вишну.html.
Each such page carries a canonical URL naming the article's number:

    <link rel="canonical" href="http://www.pravenc.ru/text/158922.html" />

so the link can be rewritten to point at 158922.md in this repository. Titles
that resolve to a disambiguation page or to nothing at all have no canonical
tag; those links are left pointing at pravenc.ru.

Resolved titles are remembered in a cache file, so the run is resumable and
re-running it costs no requests for links already seen.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

from _paths import ARTICLES_DIR, DATA_DIR

DEFAULT_CACHE_FILE = DATA_DIR / "link_cache.json"
DEFAULT_UNRESOLVED_FILE = DATA_DIR / "unresolved_links.txt"

# Markdown links to a Pravenc article, in both the plain form -- ](url) -- and
# the bracketed form markdownify uses when the URL contains spaces: ](<url>).
# Anchoring on "](" keeps the source_url in the YAML front matter untouched.
LINK_RE = re.compile(r"\]\(<?(https://pravenc\.ru/text/[^)>]+)>?\)")

CANONICAL_RE = re.compile(
    r"""<link[^>]+rel=["']canonical["'][^>]+href=["']https?://(?:www\.)?pravenc\.ru/text/(\d+)\.html["']""",
    re.IGNORECASE,
)


def fetch_html(url: str) -> str:
    """Fetch a page, returning its HTML."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.encoding = resp.apparent_encoding or resp.encoding
    resp.raise_for_status()
    return resp.text


def find_canonical_number(html: str) -> str:
    """Return the article number from the page's canonical link, or None."""
    match = CANONICAL_RE.search(html)
    return match.group(1) if match else None


def collect_links(md_files: list) -> dict:
    """Map each Pravenc article URL to the number of files that link to it."""
    urls = {}
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"    ✗ Error reading {md_file.name}: {e}", file=sys.stderr)
            continue
        for url in set(LINK_RE.findall(content)):
            urls[url] = urls.get(url, 0) + 1
    return urls


def load_cache(cache_file: Path) -> dict:
    """Load the URL -> article number cache; unresolvable URLs are stored as null."""
    if not cache_file.exists():
        return {}
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: could not read cache {cache_file}: {e}", file=sys.stderr)
        return {}


def save_cache(cache: dict, cache_file: Path) -> None:
    """Write the cache out atomically, so an interrupted run cannot corrupt it."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    tmp_file.replace(cache_file)


def resolve_urls(urls: dict, cache: dict, cache_file: Path, delay: float, limit: int) -> None:
    """Look up the article number behind each URL, filling in the cache in place."""
    pending = [url for url in sorted(urls) if url not in cache]

    if not pending:
        print("All links are already resolved in the cache; no requests needed.")
        return

    if limit and len(pending) > limit:
        print(f"Resolving {limit} of {len(pending)} unresolved links (--limit)")
        pending = pending[:limit]
    else:
        print(f"Resolving {len(pending)} unresolved links")

    try:
        for i, url in enumerate(pending, 1):
            try:
                number = find_canonical_number(fetch_html(url))
                cache[url] = number
                status = f"→ {number}" if number else "→ no canonical (left as is)"
                print(f"[{i}/{len(pending)}] {url} {status}")
            except requests.exceptions.HTTPError as e:
                # A missing page is a settled answer: there is nothing to link to.
                if e.response is not None and e.response.status_code == 404:
                    cache[url] = None
                    print(f"[{i}/{len(pending)}] {url} → 404 (left as is)")
                else:
                    print(f"[{i}/{len(pending)}] {url} ✗ {e}", file=sys.stderr)
            except Exception as e:
                # Leave transient failures out of the cache so they are retried.
                print(f"[{i}/{len(pending)}] {url} ✗ {e}", file=sys.stderr)

            if i % 100 == 0:
                save_cache(cache, cache_file)
            if i < len(pending):
                time.sleep(delay)
    except KeyboardInterrupt:
        print("\nInterrupted; saving progress so far.")
        raise
    finally:
        save_cache(cache, cache_file)


def write_unresolved(urls: dict, cache: dict, unresolved_file: Path) -> int:
    """List the URLs that carry no canonical tag, for matching up by hand later.

    Ordered by how many articles link to each one, so the titles worth the most
    effort come first.
    """
    unresolved = [url for url in urls if url in cache and not cache[url]]
    unresolved.sort(key=lambda url: (-urls[url], url))

    try:
        unresolved_file.parent.mkdir(parents=True, exist_ok=True)
        with open(unresolved_file, "w", encoding="utf-8") as f:
            for url in unresolved:
                f.write(url + "\n")
        print(f"Wrote {len(unresolved)} unresolved links to {unresolved_file}")
    except Exception as e:
        print(f"Error writing {unresolved_file}: {e}", file=sys.stderr)

    return len(unresolved)


def rewrite_files(md_files: list, cache: dict, articles_dir: Path, allow_missing: bool,
                  dry_run: bool) -> None:
    """Rewrite resolved links in each file to point at the local Markdown file."""
    known_articles = {p.stem for p in articles_dir.glob("*.md")}

    changed_files = 0
    total_links = 0
    missing_targets = set()

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"    ✗ Error reading {md_file.name}: {e}", file=sys.stderr)
            continue

        file_links = 0

        def replace_link(match):
            nonlocal file_links
            url = match.group(1)
            number = cache.get(url)
            if not number:
                return match.group(0)
            if number == md_file.stem:
                # A link from an article to itself; leave it alone.
                return match.group(0)
            if number not in known_articles:
                missing_targets.add(number)
                if not allow_missing:
                    return match.group(0)
            file_links += 1
            return f"]({number}.md)"

        new_content = LINK_RE.sub(replace_link, content)

        if file_links:
            total_links += file_links
            changed_files += 1
            if dry_run:
                print(f"🔍 Would rewrite {file_links} links in {md_file.name}")
            else:
                try:
                    md_file.write_text(new_content, encoding="utf-8")
                    print(f"✅ Rewrote {file_links} links in {md_file.name}")
                except Exception as e:
                    print(f"    ✗ Error writing {md_file.name}: {e}", file=sys.stderr)

    print("-" * 50)
    print("Link rewriting summary:")
    print(f"  Files changed: {changed_files}")
    print(f"  Links rewritten: {total_links}")
    if missing_targets:
        note = "rewritten anyway" if allow_missing else "left as is"
        print(f"  Resolved to articles not in {articles_dir.name}/: "
              f"{len(missing_targets)} ({note})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite pravenc.ru cross-references in the articles as local Markdown links")
    parser.add_argument("files", nargs="*", type=Path,
                        help="Markdown files to process (default: every article)")
    parser.add_argument("--articles-dir", type=Path, default=ARTICLES_DIR,
                        help="Directory holding the articles")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_FILE,
                        help="File caching resolved article numbers (default: data/link_cache.json)")
    parser.add_argument("--unresolved", type=Path, default=DEFAULT_UNRESOLVED_FILE,
                        help="File listing links with no canonical tag, for matching up by hand "
                             "(default: data/unresolved_links.txt)")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Delay between requests in seconds (default: 0.5)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Resolve at most this many new links this run (0 = no limit)")
    parser.add_argument("--allow-missing", action="store_true",
                        help="Rewrite links even when the target article is not in articles/")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without editing any file")
    parser.add_argument("--resolve-only", action="store_true",
                        help="Only fill the cache; do not edit any file")
    args = parser.parse_args(argv)

    articles_dir = args.articles_dir
    if not articles_dir.exists():
        print(f"Error: articles directory '{articles_dir}' not found", file=sys.stderr)
        return 1

    md_files = sorted(args.files) if args.files else sorted(articles_dir.glob("*.md"))
    if not md_files:
        print("No Markdown files to process", file=sys.stderr)
        return 1

    print(f"Scanning {len(md_files)} Markdown files for cross-references")
    urls = collect_links(md_files)
    print(f"Found {sum(urls.values())} links to {len(urls)} distinct articles")
    print("-" * 50)

    cache = load_cache(args.cache)
    print(f"Cache: {len(cache)} URLs already resolved ({args.cache})")

    try:
        resolve_urls(urls, cache, args.cache, args.delay, args.limit)
    except KeyboardInterrupt:
        return 1

    print("-" * 50)
    write_unresolved(urls, cache, args.unresolved)

    print("-" * 50)
    if args.resolve_only:
        print("Resolve-only run; no articles edited.")
        return 0

    rewrite_files(md_files, cache, articles_dir, args.allow_missing, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
