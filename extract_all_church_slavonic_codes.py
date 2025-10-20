#!/usr/bin/env python3
"""
Script to extract Church Slavonic character codes from both char/26526 and char/26528 URLs.
"""

import os
import re
from pathlib import Path

def extract_church_slavonic_codes():
    """Extract all Church Slavonic character codes from Markdown files."""
    
    # Patterns for both Church Slavonic URL types
    patterns = [
        r"https://pravenc\.ru/char/26526/([^/]+)/image\.png",
        r"https://pravenc\.ru/char/26528/([^/]+)/image\.png"
    ]
    
    all_codes = set()
    char_26526_codes = set()
    char_26528_codes = set()
    
    articles_dir = Path("articles")
    if not articles_dir.exists():
        print("Articles directory not found!")
        return
    
    print("Extracting Church Slavonic character codes...")
    print("=" * 50)
    
    # Process all Markdown files
    md_files = list(articles_dir.glob("*.md"))
    print(f"Processing {len(md_files)} Markdown files...")
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract codes from char/26526 URLs
                matches_26526 = re.findall(patterns[0], content)
                for code in matches_26526:
                    char_26526_codes.add(code)
                    all_codes.add(code)
                
                # Extract codes from char/26528 URLs
                matches_26528 = re.findall(patterns[1], content)
                for code in matches_26528:
                    char_26528_codes.add(code)
                    all_codes.add(code)
                    
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
    
    # Extract hex chunks from all codes
    all_hex_chunks = set()
    char_26526_hex_chunks = set()
    char_26528_hex_chunks = set()
    
    # Pattern to extract hex chunks (x followed by 2-3 hex digits)
    hex_pattern = r"x[0-9a-fA-F]{2,3}"
    
    for code in char_26526_codes:
        hex_chunks = re.findall(hex_pattern, code)
        for chunk in hex_chunks:
            char_26526_hex_chunks.add(chunk)
            all_hex_chunks.add(chunk)
    
    for code in char_26528_codes:
        hex_chunks = re.findall(hex_pattern, code)
        for chunk in hex_chunks:
            char_26528_hex_chunks.add(chunk)
            all_hex_chunks.add(chunk)
    
    # Print statistics
    print(f"\n📊 Extraction Results:")
    print(f"   char/26526 codes: {len(char_26526_codes)}")
    print(f"   char/26528 codes: {len(char_26528_codes)}")
    print(f"   Total unique codes: {len(all_codes)}")
    print(f"   char/26526 hex chunks: {len(char_26526_hex_chunks)}")
    print(f"   char/26528 hex chunks: {len(char_26528_hex_chunks)}")
    print(f"   Total unique hex chunks: {len(all_hex_chunks)}")
    
    # Save all hex chunks
    output_file = "all_church_slavonic_hex_chunks.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in sorted(all_hex_chunks):
            f.write(f"{chunk}\n")
    
    print(f"\n✅ All hex chunks saved to: {output_file}")
    
    # Save char/26526 hex chunks
    output_file_26526 = "char_26526_hex_chunks.txt"
    with open(output_file_26526, 'w', encoding='utf-8') as f:
        for chunk in sorted(char_26526_hex_chunks):
            f.write(f"{chunk}\n")
    
    print(f"✅ char/26526 hex chunks saved to: {output_file_26526}")
    
    # Save char/26528 hex chunks
    output_file_26528 = "char_26528_hex_chunks.txt"
    with open(output_file_26528, 'w', encoding='utf-8') as f:
        for chunk in sorted(char_26528_hex_chunks):
            f.write(f"{chunk}\n")
    
    print(f"✅ char/26528 hex chunks saved to: {output_file_26528}")
    
    # Show some examples
    print(f"\n🔍 Examples of char/26526 codes:")
    for i, code in enumerate(sorted(char_26526_codes)[:5]):
        print(f"   {i+1}. {code}")
    
    print(f"\n🔍 Examples of char/26528 codes:")
    for i, code in enumerate(sorted(char_26528_codes)[:5]):
        print(f"   {i+1}. {code}")
    
    return all_hex_chunks, char_26526_hex_chunks, char_26528_hex_chunks

if __name__ == "__main__":
    extract_church_slavonic_codes()
