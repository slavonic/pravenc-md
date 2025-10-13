#!/usr/bin/env python3
"""
Script to batch process article URLs using the scraper.
Reads URLs from a file and processes them one by one.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def process_urls_from_file(url_file: str, output_dir: str = "articles", delay: float = 0.5) -> int:
    """Process all URLs from a file using the scraper."""
    url_file_path = Path(url_file)
    
    if not url_file_path.exists():
        print(f"Error: URL file '{url_file}' not found", file=sys.stderr)
        return 1
    
    # Read URLs from file
    try:
        with open(url_file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading URL file: {e}", file=sys.stderr)
        return 1
    
    if not urls:
        print("No URLs found in file", file=sys.stderr)
        return 1
    
    print(f"Processing {len(urls)} URLs from: {url_file}")
    print(f"Output directory: {output_dir}")
    print(f"Delay between requests: {delay}s")
    print("-" * 50)
    
    successful = 0
    failed = 0
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"[{i}/{len(urls)}] Processing: {url}")
            
            # Run the scraper for this URL
            result = subprocess.run([
                sys.executable, "scrape_pravenc.py", 
                "--out-dir", output_dir, 
                url
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✓ Success: {result.stdout.strip()}")
                successful += 1
            else:
                print(f"    ✗ Failed: {result.stderr.strip()}")
                failed += 1
            
            # Be respectful to the server
            if i < len(urls):  # Don't delay after the last URL
                time.sleep(delay)
            
        except Exception as e:
            print(f"    ✗ Error processing {url}: {e}", file=sys.stderr)
            failed += 1
    
    print("-" * 50)
    print(f"Batch processing completed:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(urls)}")
    
    return 0 if failed == 0 else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Batch process article URLs using the scraper")
    parser.add_argument("url_file", help="File containing article URLs (one per line)")
    parser.add_argument("--out-dir", default="articles", help="Directory to save the Markdown files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)")
    args = parser.parse_args(argv)
    
    return process_urls_from_file(args.url_file, args.out_dir, args.delay)


if __name__ == "__main__":
    raise SystemExit(main())
