#!/usr/bin/env python3
"""
Script to extract Syriac character codes from Markdown files.
Syriac text is stored in images at https://pravenc.ru/char/26094/
Extracts hex chunks (like x40, x82DG) from full code strings.
"""

import re
from pathlib import Path

from _paths import ARTICLES_DIR, CHAR_MAPS_DIR


def extract_character_chunks(code):
    """Extract all character chunks from a code string.
    For example: 'ACx40' -> ['AC', 'x40'], 'x40x82DG' -> ['x40', 'x82DG']
    """
    chunks = []
    
    # Pattern to extract hex chunks: x followed by 2-3 hex digits, then any non-x characters
    hex_pattern = r"x[0-9a-fA-F]{2,3}[^x]*"
    
    # Find all hex chunk positions
    hex_matches = list(re.finditer(hex_pattern, code))
    
    if not hex_matches:
        # No hex chunks, return the whole code as a single chunk
        if code:
            chunks.append(code)
    else:
        # Extract prefix before first hex chunk
        first_hex_start = hex_matches[0].start()
        if first_hex_start > 0:
            prefix = code[:first_hex_start]
            if prefix:
                chunks.append(prefix)
        
        # Extract all hex chunks
        for match in hex_matches:
            chunks.append(match.group())
    
    return chunks


def extract_syriac_codes():
    """Extract all Syriac character codes and their character chunks from Markdown files."""
    
    # Pattern for Syriac URLs
    url_pattern = r"https://pravenc\.ru/char/26094/([^/]+)/image\.png"
    
    all_codes = set()
    all_chunks = set()
    
    articles_dir = ARTICLES_DIR
    if not articles_dir.exists():
        print("Articles directory not found!")
        return
    
    print("Extracting Syriac character codes...")
    print("=" * 50)
    
    # Process all Markdown files
    md_files = list(articles_dir.glob("*.md"))
    print(f"Processing {len(md_files)} Markdown files...")
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract codes from char/26094 URLs
                matches = re.findall(url_pattern, content)
                for code in matches:
                    # Clean the code (remove spaces and normalize)
                    code = code.strip()
                    if code:
                        all_codes.add(code)
                        
                        # Extract character chunks from this code
                        chunks = extract_character_chunks(code)
                        for chunk in chunks:
                            all_chunks.add(chunk)
                    
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
    
    # Print statistics
    print(f"\n📊 Extraction Results:")
    print(f"   Total unique Syriac codes: {len(all_codes)}")
    print(f"   Total unique character chunks: {len(all_chunks)}")
    
    # Save all codes
    output_file = CHAR_MAPS_DIR / "syriac_codes.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for code in sorted(all_codes):
            f.write(f"{code}\n")
    
    print(f"\n✅ All Syriac codes saved to: {output_file}")
    
    # Save character chunks
    chunks_file = CHAR_MAPS_DIR / "syriac_hex_chunks.txt"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        for chunk in sorted(all_chunks):
            f.write(f"{chunk}\n")
    
    print(f"✅ Character chunks saved to: {chunks_file}")
    
    # Show some examples
    print(f"\n🔍 Examples of Syriac codes:")
    for i, code in enumerate(sorted(all_codes)[:5]):
        chunks = extract_character_chunks(code)
        print(f"   {i+1}. {code} -> {chunks}")
    
    print(f"\n🔍 Examples of character chunks:")
    for i, chunk in enumerate(sorted(all_chunks)[:15]):
        print(f"   {i+1}. {chunk}")
    
    return all_codes, all_chunks


if __name__ == "__main__":
    extract_syriac_codes()

