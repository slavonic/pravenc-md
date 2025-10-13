#!/usr/bin/env python3
"""
Script to extract all article URLs from pravenc.ru listing pages.
Downloads pages 1-361 and extracts article URLs from <span class="article_title"><a href="..."> elements.
"""

import argparse
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def fetch_html(url: str) -> str:
    """Fetch HTML content from a URL with proper headers and encoding."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.encoding = resp.apparent_encoding or resp.encoding
    resp.raise_for_status()
    return resp.text


def extract_article_urls_from_page(html: str, base_url: str) -> list:
    """Extract article URLs from a listing page."""
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    
    # Find all spans with class "article_title" that contain links
    article_spans = soup.find_all('span', class_='article_title')
    
    for span in article_spans:
        link = span.find('a')
        if link and link.get('href'):
            # Convert relative URL to absolute URL
            article_url = urljoin(base_url, link.get('href'))
            urls.append(article_url)
    
    return urls


def extract_all_article_urls(start_page: int = 1, end_page: int = 361, output_file: str = "article_urls.txt") -> int:
    """Extract all article URLs from pravenc.ru listing pages."""
    all_urls = []
    base_url = "https://pravenc.ru/"
    
    print(f"Extracting article URLs from pages {start_page} to {end_page}")
    print(f"Output file: {output_file}")
    print("-" * 50)
    
    for page_num in range(start_page, end_page + 1):
        try:
            url = f"https://pravenc.ru/list.html?t_page={page_num}"
            print(f"[{page_num}/{end_page}] Fetching: {url}")
            
            # Fetch the page
            html = fetch_html(url)
            
            # Extract article URLs from this page
            page_urls = extract_article_urls_from_page(html, base_url)
            all_urls.extend(page_urls)
            
            print(f"    ✓ Found {len(page_urls)} articles")
            
            # Be respectful to the server
            time.sleep(0.5)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"    → Page {page_num} not found (404), stopping.")
                break
            else:
                print(f"    ✗ HTTP Error {e.response.status_code}: {e}", file=sys.stderr)
                continue
        except Exception as e:
            print(f"    ✗ Error processing page {page_num}: {e}", file=sys.stderr)
            continue
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen_urls = set()
    for url in all_urls:
        if url not in seen_urls:
            unique_urls.append(url)
            seen_urls.add(url)
    
    # Save URLs to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in unique_urls:
                f.write(url + '\n')
        
        print("-" * 50)
        print(f"Successfully extracted {len(unique_urls)} unique article URLs")
        print(f"URLs saved to: {output_file}")
        print(f"Total URLs found: {len(all_urls)} (removed {len(all_urls) - len(unique_urls)} duplicates)")
        
        return 0
        
    except Exception as e:
        print(f"Error saving URLs to file: {e}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract all article URLs from pravenc.ru listing pages")
    parser.add_argument("--start-page", type=int, default=1, help="Starting page number (default: 1)")
    parser.add_argument("--end-page", type=int, default=361, help="Ending page number (default: 361)")
    parser.add_argument("--output", default="article_urls.txt", help="Output file for URLs (default: article_urls.txt)")
    args = parser.parse_args(argv)
    
    return extract_all_article_urls(args.start_page, args.end_page, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
