#!/usr/bin/env python3
import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import yaml


def sanitize_filename(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-._]", "", text)
    text = re.sub(r"-+", "-", text)
    return text[:120] or "article"


def url_to_basename(url: str) -> str:
    m = re.search(r"/(\d+)(?:\.html)?$", url)
    if m:
        return m.group(1)
    last = url.rstrip("/").split("/")[-1]
    last = last.split("?")[0]
    last = last.replace(".html", "")
    return sanitize_filename(last)


def fetch_html(url: str) -> str:
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


def absolutize_urls(element: BeautifulSoup, base_url: str) -> None:
    # Convert <a href> and <img src> (and common media) to absolute URLs
    for tag in element.find_all(["a", "img", "source", "audio", "video"]):
        if tag.name == "a" and tag.has_attr("href"):
            absolute_url = urljoin(base_url, tag.get("href"))
            # Wrap URLs with spaces in angle brackets for proper Markdown
            if " " in absolute_url:
                tag["href"] = f"<{absolute_url}>"
            else:
                tag["href"] = absolute_url
        elif tag.name in ("img", "source") and tag.has_attr("src"):
            absolute_url = urljoin(base_url, tag.get("src"))
            if " " in absolute_url:
                tag["src"] = f"<{absolute_url}>"
            else:
                tag["src"] = absolute_url
        elif tag.name in ("audio", "video"):
            if tag.has_attr("src"):
                absolute_url = urljoin(base_url, tag.get("src"))
                if " " in absolute_url:
                    tag["src"] = f"<{absolute_url}>"
                else:
                    tag["src"] = absolute_url
            for src in tag.find_all("source"):
                if src.has_attr("src"):
                    absolute_url = urljoin(base_url, src.get("src"))
                    if " " in absolute_url:
                        src["src"] = f"<{absolute_url}>"
                    else:
                        src["src"] = absolute_url


def extract_fields(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1.article_title[itemprop=title]")
    author_el = soup.select_one("div.author")
    content_el = soup.select_one("div.article_text")
    info_el = soup.select_one("div.info")

    if content_el is None:
        raise ValueError("Could not find div.article_text in the page")

    # Make URLs absolute inside the content block before converting to Markdown
    absolutize_urls(content_el, base_url)

    article_title = title_el.get_text(strip=True) if title_el else ""
    author_html = author_el.decode_contents() if author_el else ""

    # Extract volume and page numbers from div.info
    volume = ""
    page_numbers = ""
    
    if info_el:
        # Find volume number in <a> tag
        volume_link = info_el.find("a")
        if volume_link:
            volume = volume_link.get_text(strip=True)
        
        # Find page numbers in format "С. [numbers]"
        info_text = info_el.get_text()
        page_match = re.search(r"С\.\s*([0-9,\s\-]+)", info_text)
        if page_match:
            page_numbers = page_match.group(1).strip()

    content_md = md(
        str(content_el),
        heading_style="ATX",
        convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
        bullets="-",
    ).strip()

    return {
        "article_title": article_title,
        "author_html": author_html.strip(),
        "volume": volume,
        "page_numbers": page_numbers,
        "content_md": content_md,
    }


def build_front_matter(article_title: str, author_html: str, volume: str, page_numbers: str, source_url: str) -> str:
    author_text = BeautifulSoup(author_html, "html.parser").get_text(" ", strip=True) if author_html else ""

    data = {
        "article_title": article_title or None,
        "author": author_text or None,
        "volume": volume or None,
        "page_numbers": page_numbers or None,
        "source_url": source_url,
        "downloaded_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }

    data = {k: v for k, v in data.items() if v not in (None, "")}
    yaml_str = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{yaml_str}\n---\n"


def save_markdown(output_dir: Path, base_name: str, front_matter: str, content_md: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{base_name}.md"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(front_matter)
        f.write("\n")
        f.write(content_md)
        f.write("\n")
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Download and convert Pravenc article to Markdown with YAML front matter")
    parser.add_argument("url", nargs="?", default="https://pravenc.ru/text/71893.html", help="Article URL to download")
    parser.add_argument("--out-dir", default="articles", help="Directory to save the Markdown file")
    args = parser.parse_args(argv)

    url = args.url
    try:
        html = fetch_html(url)
        fields = extract_fields(html, base_url=url)
        front_matter = build_front_matter(
            article_title=fields["article_title"],
            author_html=fields["author_html"],
            volume=fields["volume"],
            page_numbers=fields["page_numbers"],
            source_url=url,
        )
        base_name = url_to_basename(url)
        out_path = save_markdown(Path(args.out_dir), base_name, front_matter, fields["content_md"])
        print(str(out_path))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
