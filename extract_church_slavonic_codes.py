#!/usr/bin/env python3
"""
Script to extract Church Slavonic character codes from image URLs in Markdown files.
Finds URLs of the form: https://pravenc.ru/char/[number]/[code]/image.png
Extracts hex chunks (x followed by 2-3 hex digits) from the codes.
"""

import re
import os
from pathlib import Path
from collections import OrderedDict


def find_church_slavonic_urls(content):
    """
    Find all Church Slavonic character image URLs in the content.
    Pattern: https://pravenc.ru/char/[number]/[code]/image.png
    """
    # Pattern to match the Church Slavonic character URLs
    pattern = r'https://pravenc\.ru/char/(\d+)/([^/]+)/image\.png'
    matches = re.findall(pattern, content)
    return matches


def extract_hex_chunks(code):
    """
    Extract hex chunks from a character code.
    Chunks are of the form: x followed by 2-3 hexadecimal digits
    Example: xc04xecxefxebixe9 -> ['xc04', 'xec', 'xef', 'xeb', 'xe9']
    """
    # Pattern to match x followed by 2-3 hex digits
    pattern = r'x[0-9a-fA-F]{2,3}'
    chunks = re.findall(pattern, code)
    return chunks


def process_markdown_files(articles_dir):
    """
    Process all Markdown files in the articles directory.
    Extract Church Slavonic character codes and their hex chunks.
    """
    articles_path = Path(articles_dir)
    if not articles_path.exists():
        print(f"Error: Articles directory '{articles_dir}' not found")
        return set()
    
    all_hex_chunks = set()
    total_files = 0
    files_with_codes = 0
    total_codes = 0
    
    print(f"Processing Markdown files in: {articles_dir}")
    print("-" * 50)
    
    # Process all .md files
    for md_file in articles_path.glob("*.md"):
        total_files += 1
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find Church Slavonic URLs
            url_matches = find_church_slavonic_urls(content)
            
            if url_matches:
                files_with_codes += 1
                total_codes += len(url_matches)
                
                print(f"Found {len(url_matches)} codes in: {md_file.name}")
                
                # Extract hex chunks from each code
                for number, code in url_matches:
                    hex_chunks = extract_hex_chunks(code)
                    all_hex_chunks.update(hex_chunks)
                    
                    if hex_chunks:  # Only print if we found chunks
                        print(f"  Code: {code} -> Chunks: {hex_chunks}")
        
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
            continue
    
    print("-" * 50)
    print(f"Summary:")
    print(f"  Total files processed: {total_files}")
    print(f"  Files with Church Slavonic codes: {files_with_codes}")
    print(f"  Total character codes found: {total_codes}")
    print(f"  Unique hex chunks found: {len(all_hex_chunks)}")
    
    return all_hex_chunks


def save_hex_chunks(hex_chunks, output_file):
    """
    Save unique hex chunks to a text file, one per line.
    """
    # Sort the chunks for consistent output
    sorted_chunks = sorted(hex_chunks)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in sorted_chunks:
                f.write(chunk + '\n')
        
        print(f"\nSaved {len(sorted_chunks)} unique hex chunks to: {output_file}")
        
    except Exception as e:
        print(f"Error saving to {output_file}: {e}")


def main():
    """Main function to extract Church Slavonic character codes."""
    articles_dir = "articles"
    output_file = "church_slavonic_hex_chunks.txt"
    
    print("Church Slavonic Character Code Extractor")
    print("=" * 50)
    
    # Process all Markdown files
    hex_chunks = process_markdown_files(articles_dir)
    
    if hex_chunks:
        # Save the unique hex chunks
        save_hex_chunks(hex_chunks, output_file)
        
        # Show some examples
        print(f"\nFirst 10 hex chunks found:")
        for i, chunk in enumerate(sorted(hex_chunks)[:10]):
            print(f"  {i+1:2d}. {chunk}")
        
        if len(hex_chunks) > 10:
            print(f"  ... and {len(hex_chunks) - 10} more")
    else:
        print("\nNo Church Slavonic character codes found.")


if __name__ == "__main__":
    main()
