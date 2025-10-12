#!/usr/bin/env python3
import argparse
import datetime as dt
import re
import sys
import time
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


def get_next_article_url(html: str, current_url: str) -> str:
    """Extract the URL of the next article from the 'следующая статья' link."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Look for the "следующая статья" link
    next_link = soup.find("a", string="следующая статья")
    if next_link and next_link.get("href"):
        # Convert relative URL to absolute URL
        next_url = urljoin(current_url, next_link.get("href"))
        return next_url
    
    return None


def process_content_with_references(content_el: BeautifulSoup, base_url: str) -> str:
    """Process content element and convert reference divs to headings in place."""
    # First, convert the main content to Markdown to find existing heading levels
    main_content = content_el.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    # Find existing heading levels in the content
    heading_levels = []
    for element in main_content:
        if element.name and element.name.startswith('h') and element.name[1:].isdigit():
            level = int(element.name[1:])
            heading_levels.append(level)
    
    # Determine reference heading level (one below the highest existing heading)
    # If there are headings, use one level below the minimum; otherwise use h1
    if heading_levels:
        reference_level = min(heading_levels) + 1
        # Don't go beyond h6
        reference_level = min(reference_level, 6)
    else:
        reference_level = 1
    reference_prefix = '#' * reference_level
    
    # Find all reference divs in the content (they might be nested)
    reference_divs = content_el.find_all('div', class_='reference')
    
    # Process content and build Markdown sections
    markdown_parts = []
    
    for child in content_el.children:
        if hasattr(child, 'name') and child.name == 'div' and child.get('class') and 'content' in child.get('class'):
            # Skip Содержание (Table of Contents) sections
            continue
        elif hasattr(child, 'name') and child.name == 'div' and child.get_text(strip=True).startswith('Содержание'):
            # Skip any div that starts with "Содержание"
            continue
        elif hasattr(child, 'name') and child.name == 'div' and child.get('class') and 'toc' in child.get('class'):
            # Skip Table of Contents div
            continue
        elif hasattr(child, 'name') and child.name == 'h1' and child.get('class') and 'article_title' in child.get('class'):
            # Skip the main article title (it's already in metadata)
            continue
        elif hasattr(child, 'name') and child.name == 'div' and not child.get('class'):
            # This is likely the main content div - process it specially to handle nested references
            process_nested_content(child, reference_divs, reference_prefix, base_url, markdown_parts)
        else:
            # Regular content - convert to Markdown
            if hasattr(child, 'name') and child.name:
                child_md = md(
                    str(child),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
                if child_md:
                    markdown_parts.append(child_md)
            elif str(child).strip():
                # Handle text nodes
                text_content = str(child).strip()
                if text_content:
                    markdown_parts.append(text_content)
    
    # Join all Markdown parts
    content_md = '\n\n'.join(markdown_parts).strip()
    
    return content_md


def process_nested_content(content_div: BeautifulSoup, reference_divs: list, reference_prefix: str, base_url: str, markdown_parts: list) -> None:
    """Process a content div that may contain nested reference divs."""
    # Process content section by section
    current_section = []
    
    for element in content_div.children:
        if hasattr(element, 'name') and element.name == 'div' and element.get('class') and 'reference' in element.get('class'):
            # This is a direct reference div - add current section and then the reference
            if current_section:
                section_html = ''.join(current_section)
                section_md = md(
                    section_html,
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
                if section_md:
                    markdown_parts.append(section_md)
                current_section = []
            
            # Add the reference with appropriate heading
            absolutize_urls(element, base_url)
            
            # Detect literature type and remove abbreviation
            ref_text = element.get_text(strip=True)
            heading_text = "Литература"  # default
            
            if ref_text.startswith("Соч.:"):
                heading_text = "Сочинения"
                # Remove the abbreviation from the content
                element_copy = BeautifulSoup(str(element), 'html.parser')
                # Find and remove text nodes that start with "Соч.:"
                for text_node in element_copy.find_all(string=True):
                    if text_node.strip().startswith("Соч.:"):
                        text_node.replace_with(text_node.strip()[5:])  # Remove "Соч.:"
                ref_md = md(
                    str(element_copy),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            elif ref_text.startswith("Ист.:"):
                heading_text = "Источники"
                # Remove the abbreviation from the content
                element_copy = BeautifulSoup(str(element), 'html.parser')
                for text_node in element_copy.find_all(string=True):
                    if text_node.strip().startswith("Ист.:"):
                        text_node.replace_with(text_node.strip()[5:])  # Remove "Ист.:"
                ref_md = md(
                    str(element_copy),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            elif ref_text.startswith("Лит.:"):
                heading_text = "Литература"
                # Remove the abbreviation from the content
                element_copy = BeautifulSoup(str(element), 'html.parser')
                for text_node in element_copy.find_all(string=True):
                    if text_node.strip().startswith("Лит.:"):
                        text_node.replace_with(text_node.strip()[5:])  # Remove "Лит.:"
                ref_md = md(
                    str(element_copy),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            else:
                # No abbreviation found, use original content
                ref_md = md(
                    str(element),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            
            markdown_parts.append(f"{reference_prefix} {heading_text}\n\n{ref_md}")
        elif hasattr(element, 'name') and element.name:
            # Check if this element contains reference divs
            refs_in_element = element.find_all('div', class_='reference')
            
            if refs_in_element:
                # This element contains references - process it specially
                # First add current section
                if current_section:
                    section_html = ''.join(current_section)
                    section_md = md(
                        section_html,
                        heading_style="ATX",
                        convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                        bullets="-",
                    ).strip()
                    if section_md:
                        markdown_parts.append(section_md)
                    current_section = []
                
                # Process the element with references
                process_element_with_references(element, refs_in_element, reference_prefix, base_url, markdown_parts)
            else:
                # Regular content - add to current section
                current_section.append(str(element))
        elif str(element).strip():
            current_section.append(str(element))
    
    # Add any remaining content
    if current_section:
        section_html = ''.join(current_section)
        section_md = md(
            section_html,
            heading_style="ATX",
            convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
            bullets="-",
        ).strip()
        if section_md:
            markdown_parts.append(section_md)


def process_element_with_references(element: BeautifulSoup, reference_divs: list, reference_prefix: str, base_url: str, markdown_parts: list) -> None:
    """Process an element that contains reference divs."""
    # Process the element content section by section
    current_section = []
    
    for child in element.children:
        if hasattr(child, 'name') and child.name == 'div' and child.get('class') and 'reference' in child.get('class'):
            # This is a reference div - add current section and then the reference
            if current_section:
                section_html = ''.join(current_section)
                section_md = md(
                    section_html,
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
                if section_md:
                    markdown_parts.append(section_md)
                current_section = []
            
            # Add the reference with appropriate heading
            absolutize_urls(child, base_url)
            
            # Detect literature type and remove abbreviation
            ref_text = child.get_text(strip=True)
            heading_text = "Литература"  # default
            
            if ref_text.startswith("Соч.:"):
                heading_text = "Сочинения"
                # Remove the abbreviation from the content
                child_copy = BeautifulSoup(str(child), 'html.parser')
                # Find and remove text nodes that start with "Соч.:"
                for text_node in child_copy.find_all(string=True):
                    if text_node.strip().startswith("Соч.:"):
                        text_node.replace_with(text_node.strip()[5:])  # Remove "Соч.:"
                ref_md = md(
                    str(child_copy),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            elif ref_text.startswith("Ист.:"):
                heading_text = "Источники"
                # Remove the abbreviation from the content
                child_copy = BeautifulSoup(str(child), 'html.parser')
                for text_node in child_copy.find_all(string=True):
                    if text_node.strip().startswith("Ист.:"):
                        text_node.replace_with(text_node.strip()[5:])  # Remove "Ист.:"
                ref_md = md(
                    str(child_copy),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            elif ref_text.startswith("Лит.:"):
                heading_text = "Литература"
                # Remove the abbreviation from the content
                child_copy = BeautifulSoup(str(child), 'html.parser')
                for text_node in child_copy.find_all(string=True):
                    if text_node.strip().startswith("Лит.:"):
                        text_node.replace_with(text_node.strip()[5:])  # Remove "Лит.:"
                ref_md = md(
                    str(child_copy),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            else:
                # No abbreviation found, use original content
                ref_md = md(
                    str(child),
                    heading_style="ATX",
                    convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
                    bullets="-",
                ).strip()
            
            markdown_parts.append(f"{reference_prefix} {heading_text}\n\n{ref_md}")
        else:
            # Regular content - add to current section
            if hasattr(child, 'name') and child.name:
                current_section.append(str(child))
            elif str(child).strip():
                current_section.append(str(child))
    
    # Add any remaining content
    if current_section:
        section_html = ''.join(current_section)
        section_md = md(
            section_html,
            heading_style="ATX",
            convert=['br', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'code', 'pre'],
            bullets="-",
        ).strip()
        if section_md:
            markdown_parts.append(section_md)


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
    author_els = soup.select("div.author")  # Get all author divs
    content_el = soup.select_one("div.article_text")
    info_el = soup.select_one("div.info")

    if content_el is None:
        raise ValueError("Could not find div.article_text in the page")

    # Make URLs absolute inside the content block before converting to Markdown
    absolutize_urls(content_el, base_url)

    article_title = title_el.get_text(strip=True) if title_el else ""
    
    # Extract all author names, remove duplicates, and join with commas
    all_authors = []
    for author_el in author_els:
        author_text = author_el.get_text(strip=True)
        if author_text:
            # Split by comma in case multiple authors are in one div
            individual_authors = [a.strip() for a in author_text.split(',')]
            all_authors.extend(individual_authors)
    
    # Remove duplicates while preserving order
    seen_authors = set()
    unique_authors = []
    for author in all_authors:
        if author and author not in seen_authors:
            unique_authors.append(author)
            seen_authors.add(author)
    
    author_html = ", ".join(unique_authors)

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

    # Process content with references in place
    content_md = process_content_with_references(content_el, base_url)

    return {
        "article_title": article_title,
        "author_html": author_html,
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


def download_all_articles(start_url: str, output_dir: str) -> int:
    """Download all articles starting from start_url, following 'следующая статья' links."""
    current_url = start_url
    article_count = 0
    
    print(f"Starting to download articles from: {start_url}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)
    
    while current_url:
        try:
            print(f"[{article_count + 1}] Processing: {current_url}")
            
            # Fetch the article
            html = fetch_html(current_url)
            
            # Check if we got a 404 error page
            if "404 ошибка" in html or "Такого документа нет" in html:
                print(f"Reached end of articles (404 error) at: {current_url}")
                break
            
            # Process the article
            fields = extract_fields(html, base_url=current_url)
            front_matter = build_front_matter(
                article_title=fields["article_title"],
                author_html=fields["author_html"],
                volume=fields["volume"],
                page_numbers=fields["page_numbers"],
                source_url=current_url,
            )
            base_name = url_to_basename(current_url)
            out_path = save_markdown(Path(output_dir), base_name, front_matter, fields["content_md"])
            
            article_count += 1
            print(f"    ✓ Saved: {out_path}")
            print(f"    ✓ Title: {fields['article_title']}")
            
            # Get the next article URL
            next_url = get_next_article_url(html, current_url)
            if next_url:
                current_url = next_url
                print(f"    → Next: {current_url}")
            else:
                print("    → No next article found, stopping.")
                break
            
            # Pause to be respectful to the server
            time.sleep(0.5)
            print()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"Reached end of articles (HTTP 404) at: {current_url}")
                break
            else:
                print(f"HTTP Error {e.response.status_code}: {e}", file=sys.stderr)
                break
        except Exception as e:
            print(f"Error processing {current_url}: {e}", file=sys.stderr)
            break
    
    print("-" * 50)
    print(f"Download completed. Processed {article_count} articles.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Download and convert Pravenc article(s) to Markdown with YAML front matter")
    parser.add_argument("url", nargs="?", default="https://pravenc.ru/text/71893.html", help="Article URL to download (or starting URL for --all)")
    parser.add_argument("--out-dir", default="articles", help="Directory to save the Markdown file(s)")
    parser.add_argument("--all", action="store_true", help="Download all articles starting from the given URL")
    args = parser.parse_args(argv)

    if args.all:
        return download_all_articles(args.url, args.out_dir)
    else:
        # Single article download (original functionality)
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
