#!/usr/bin/env python3
"""
Script to convert Church Slavonic image references to Unicode text using the mapping from cu.json.
"""

import json
import re
import os
from pathlib import Path

def load_mapping(mapping_file):
    """Load the Church Slavonic character mapping from JSON file."""
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"✅ Loaded {len(mapping)} character mappings from {mapping_file}")
        return mapping
    except Exception as e:
        print(f"❌ Error loading mapping file {mapping_file}: {e}")
        return {}

def convert_church_slavonic_images(content, mapping):
    """Convert Church Slavonic image references to Unicode text."""
    
    # Pattern to match Church Slavonic image URLs
    # Matches both char/26526 and char/26528 patterns
    # Handles spaces and special characters in the code sequence
    pattern = r'!\[\]\(<https://pravenc\.ru/char/(26526|26528)/([^>]+)>\)'
    
    def replace_image(match):
        char_type = match.group(1)  # 26526 or 26528
        code_sequence = match.group(2)  # The character code sequence
        
        # Remove /image.png if present and clean up the sequence
        code_sequence = code_sequence.replace('/image.png', '').strip()
        
        # Skip empty sequences
        if not code_sequence:
            return ''
        
        # Split the sequence into parts, preserving spaces
        # First, extract hex chunks
        hex_chunks = re.findall(r'x[0-9a-fA-F]{2,3}', code_sequence)
        
        # Convert each hex chunk to Unicode using the mapping
        unicode_chars = []
        for chunk in hex_chunks:
            if chunk in mapping:
                unicode_chars.append(mapping[chunk])
            else:
                # If chunk not found in mapping, keep the original chunk
                unicode_chars.append(f"[{chunk}]")
        
        # Handle spaces: if there are spaces in the original sequence, preserve them
        # We need to reconstruct the text with proper spacing
        result_text = ''
        remaining_sequence = code_sequence
        
        for chunk in hex_chunks:
            # Find the position of this chunk in the remaining sequence
            chunk_pos = remaining_sequence.find(chunk)
            if chunk_pos > 0:
                # There's text before this chunk (likely spaces)
                prefix = remaining_sequence[:chunk_pos]
                # Convert spaces to actual spaces
                prefix = prefix.replace(' ', ' ')
                result_text += prefix
            
            # Add the converted character
            if chunk in mapping:
                result_text += mapping[chunk]
            else:
                result_text += f"[{chunk}]"
            
            # Remove the processed part from remaining sequence
            remaining_sequence = remaining_sequence[chunk_pos + len(chunk):]
        
        # Add any remaining text (spaces at the end)
        if remaining_sequence:
            remaining_sequence = remaining_sequence.replace(' ', ' ')
            result_text += remaining_sequence
        
        # Wrap in span with Church Slavonic class
        return f'<span class="cu">{result_text}</span>'
    
    # Replace all Church Slavonic image references
    converted_content = re.sub(pattern, replace_image, content)
    
    return converted_content

def process_markdown_files(articles_dir, mapping, dry_run=False):
    """Process all Markdown files to convert Church Slavonic images to Unicode."""
    
    articles_path = Path(articles_dir)
    if not articles_path.exists():
        print(f"❌ Articles directory not found: {articles_dir}")
        return
    
    md_files = list(articles_path.glob("*.md"))
    print(f"📁 Found {len(md_files)} Markdown files to process")
    
    total_conversions = 0
    processed_files = 0
    
    for md_file in md_files:
        try:
            # Read the file
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Convert Church Slavonic images
            converted_content = convert_church_slavonic_images(content, mapping)
            
            # Count conversions using the same pattern as the conversion function
            original_images = len(re.findall(r'!\[\]\(<https://pravenc\.ru/char/(26526|26528)/([^>]+)>\)', content))
            if original_images > 0:
                total_conversions += original_images
                processed_files += 1
                
                if not dry_run:
                    # Write the converted content back
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(converted_content)
                    print(f"✅ Converted {original_images} Church Slavonic images in {md_file.name}")
                else:
                    print(f"🔍 Would convert {original_images} Church Slavonic images in {md_file.name}")
                    
        except Exception as e:
            print(f"❌ Error processing {md_file}: {e}")
    
    print(f"\n📊 Conversion Summary:")
    print(f"   Files processed: {processed_files}")
    print(f"   Total conversions: {total_conversions}")
    
    return total_conversions

def main():
    """Main function to convert Church Slavonic images to Unicode."""
    
    print("Church Slavonic Image to Unicode Converter")
    print("=" * 50)
    print("This script converts Church Slavonic image references to Unicode text")
    print("wrapped in <span class='cu'> tags for proper font styling.")
    print()
    
    # Load the mapping
    mapping_file = "cu.json"
    mapping = load_mapping(mapping_file)
    
    if not mapping:
        print("❌ No mapping loaded. Exiting.")
        return
    
    # Show example conversion
    print("📝 Example conversion:")
    print("   Before: ![](https://pravenc.ru/char/26528/x010/image.png)")
    print("   After:  <span class='cu'>ⷣ҇</span>")
    print()
    
    # Ask user if they want to do a dry run first
    print(f"\n🔍 Options:")
    print(f"   1. Dry run (show what would be converted)")
    print(f"   2. Convert all files")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\n🔍 Running dry run...")
        process_markdown_files("articles", mapping, dry_run=True)
        
        print(f"\n❓ Do you want to proceed with the actual conversion? (y/n): ", end="")
        proceed = input().strip().lower()
        if proceed == 'y':
            print("\n🔄 Converting files...")
            process_markdown_files("articles", mapping, dry_run=False)
        else:
            print("❌ Conversion cancelled.")
            
    elif choice == "2":
        print("\n🔄 Converting files...")
        process_markdown_files("articles", mapping, dry_run=False)
    else:
        print("❌ Invalid choice. Exiting.")

if __name__ == "__main__":
    main()
